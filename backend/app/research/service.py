import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider
from app.research.schemas import ResearchCitation, ResearchFinding, ResearchReport
from app.retrieval.schemas import SearchResultItem
from app.retrieval.service import search

# Research pulls broadly across the whole knowledge base -- not a
# user-picked document set like comparison/reports -- so it asks retrieval
# for more candidates than a normal chat turn would.
RESEARCH_TOP_K = 15

_SYSTEM_PROMPT = (
    "You are researching a topic across a knowledge base. You are given a numbered "
    "list of excerpts retrieved from the organization's documents. Produce findings "
    "using ONLY what the excerpts actually say -- never add outside knowledge, and "
    "never state a finding that isn't grounded in at least one excerpt. Respond with "
    'ONLY a JSON object, nothing else: {"summary": "<2-3 sentence overview of what '
    'the knowledge base shows about this topic>", "findings": [{"claim": "<a '
    'specific, grounded finding>", "sources": [<excerpt numbers that support this '
    'exact claim>]}], "gaps": ["<aspects of the topic the excerpts don\'t address>"]}. '
    "Every finding must list the excerpt numbers that actually support it -- omit any "
    "finding you can't point to a specific excerpt for."
)


class ResearchUnavailableError(Exception):
    """The LLM call failed or its response couldn't be parsed."""


def _numbered_excerpts(results: list[SearchResultItem]) -> str:
    return "\n\n".join(
        f"[{i + 1}] (from {r.filename}, page {r.page_number}):\n{r.text}" for i, r in enumerate(results)
    )


def _parse_research(raw: str) -> dict | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        findings = [
            {"claim": str(item["claim"]), "sources": [int(n) for n in item.get("sources", []) if isinstance(n, (int, float))]}
            for item in data["findings"]
        ]
        return {
            "summary": str(data["summary"]),
            "findings": findings,
            "gaps": [str(item) for item in data.get("gaps", [])],
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _citation_from_result(result: SearchResultItem) -> ResearchCitation:
    return ResearchCitation(
        chunk_id=str(result.chunk_id),
        document_id=str(result.document_id),
        filename=result.filename,
        page_number=result.page_number,
        snippet=result.text[:280],
    )


async def research_topic(db: AsyncSession, organization_id: uuid.UUID, topic: str) -> ResearchReport:
    results = await search(db, organization_id, topic, top_k=RESEARCH_TOP_K)
    if not results:
        return ResearchReport(
            topic=topic,
            summary="No relevant content was found in this workspace's knowledge base for this topic.",
            findings=[],
            gaps=[topic],
            documents_used=[],
        )

    try:
        provider = get_llm_provider()
        raw = provider.generate(_SYSTEM_PROMPT, f"Research topic: {topic}\n\n{_numbered_excerpts(results)}")
    except LLMNotConfiguredError as exc:
        raise ResearchUnavailableError(str(exc)) from exc
    except LLMGenerationError as exc:
        raise ResearchUnavailableError(str(exc)) from exc

    parsed = _parse_research(raw)
    if parsed is None:
        raise ResearchUnavailableError("The AI provider returned a response that couldn't be parsed")

    findings: list[ResearchFinding] = []
    documents_used: set[str] = set()
    for item in parsed["findings"]:
        # Only an in-range excerpt number can back a finding -- these are
        # real retrieved chunks, never text the LLM invented, so an
        # out-of-range or missing index just means "not actually cited."
        cited_results = [results[n - 1] for n in item["sources"] if 1 <= n <= len(results)]
        if not cited_results:
            continue

        distinct_documents = {r.document_id for r in cited_results}
        confidence = "verified" if len(distinct_documents) >= 2 else "single_source"
        citations = [_citation_from_result(r) for r in cited_results]
        documents_used.update(c.filename for c in citations)

        findings.append(ResearchFinding(claim=item["claim"], confidence=confidence, citations=citations))

    return ResearchReport(
        topic=topic,
        summary=parsed["summary"],
        findings=findings,
        gaps=parsed["gaps"],
        documents_used=sorted(documents_used),
    )
