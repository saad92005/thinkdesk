import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider
from app.intelligence.schemas import ComparisonResult, ExtractedField, ExtractionResult, ReportResult
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus

# Keeps two documents' combined text comfortably inside a free-tier LLM's
# context window. A truncated comparison is flagged to the caller, never
# silently passed off as a complete one.
MAX_CHARS_PER_DOCUMENT = 12000

_SYSTEM_PROMPT = (
    "You compare two documents and report ONLY what is actually present in the "
    "excerpts given -- never invent content that isn't there. Respond with ONLY a "
    'JSON object, nothing else: {"summary": "<one or two sentence overview>", '
    '"similarities": ["..."], "differences": ["..."], "contradictions": ["..."]}. '
    "Each list item is a short, specific sentence grounded in the text. "
    '"contradictions" means the two documents state things that cannot both be '
    "true -- leave that list empty if there are none; don't force an entry."
)


class DocumentNotFoundError(Exception):
    """One or both documents don't exist in this organization."""


class DocumentNotReadyError(Exception):
    """A document hasn't finished processing (no chunks yet) -- comparing
    it would silently compare against nothing, so this is surfaced
    instead."""


class ComparisonUnavailableError(Exception):
    """The LLM call failed or its response couldn't be parsed."""


class ExtractionUnavailableError(Exception):
    """The LLM call failed or its response couldn't be parsed."""


class ReportUnavailableError(Exception):
    """The LLM call failed or its response couldn't be parsed."""


async def _load_document_text(db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID) -> tuple[Document, str]:
    document = await db.get(Document, document_id)
    if document is None or document.organization_id != organization_id:
        raise DocumentNotFoundError(str(document_id))
    if document.status != DocumentStatus.READY:
        raise DocumentNotReadyError(document.filename)

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = list(result.scalars().all())
    return document, "\n\n".join(chunk.text for chunk in chunks)


def _truncate(text: str, limit: int = MAX_CHARS_PER_DOCUMENT) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def _parse_comparison(raw: str) -> dict | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return {
            "summary": str(data["summary"]),
            "similarities": [str(item) for item in data.get("similarities", [])],
            "differences": [str(item) for item in data.get("differences", [])],
            "contradictions": [str(item) for item in data.get("contradictions", [])],
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


async def compare_documents(
    db: AsyncSession, organization_id: uuid.UUID, document_id_a: uuid.UUID, document_id_b: uuid.UUID
) -> ComparisonResult:
    doc_a, text_a = await _load_document_text(db, organization_id, document_id_a)
    doc_b, text_b = await _load_document_text(db, organization_id, document_id_b)

    text_a, truncated_a = _truncate(text_a)
    text_b, truncated_b = _truncate(text_b)
    truncated = truncated_a or truncated_b

    prompt = (
        f"Document A ({doc_a.filename}){' [truncated]' if truncated_a else ''}:\n{text_a}\n\n"
        f"Document B ({doc_b.filename}){' [truncated]' if truncated_b else ''}:\n{text_b}"
    )

    try:
        provider = get_llm_provider()
        raw = provider.generate(_SYSTEM_PROMPT, prompt)
    except LLMNotConfiguredError as exc:
        raise ComparisonUnavailableError(str(exc)) from exc
    except LLMGenerationError as exc:
        raise ComparisonUnavailableError(str(exc)) from exc

    parsed = _parse_comparison(raw)
    if parsed is None:
        raise ComparisonUnavailableError("The AI provider returned a response that couldn't be parsed")

    return ComparisonResult(document_a=doc_a.filename, document_b=doc_b.filename, truncated=truncated, **parsed)


_EXTRACTION_SYSTEM_PROMPT = (
    "You extract key structured facts from a document -- dates, deadlines, "
    "monetary amounts, named parties/organizations, obligations, and other "
    "concrete facts a reader would want at a glance. Extract ONLY facts "
    "actually stated in the text -- never infer or invent one. Respond with "
    'ONLY a JSON object, nothing else: {"fields": [{"label": "<short field '
    'name>", "value": "<the extracted fact>"}, ...]}. If the document has no '
    "such extractable facts, return an empty fields list rather than forcing "
    "an entry."
)


def _parse_extraction(raw: str) -> list[ExtractedField] | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return [ExtractedField(label=str(item["label"]), value=str(item["value"])) for item in data["fields"]]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


async def extract_key_information(
    db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID
) -> ExtractionResult:
    document, text = await _load_document_text(db, organization_id, document_id)
    text, truncated = _truncate(text)

    try:
        provider = get_llm_provider()
        raw = provider.generate(_EXTRACTION_SYSTEM_PROMPT, text)
    except LLMNotConfiguredError as exc:
        raise ExtractionUnavailableError(str(exc)) from exc
    except LLMGenerationError as exc:
        raise ExtractionUnavailableError(str(exc)) from exc

    fields = _parse_extraction(raw)
    if fields is None:
        raise ExtractionUnavailableError("The AI provider returned a response that couldn't be parsed")

    return ExtractionResult(document=document.filename, fields=fields, truncated=truncated)


# Smaller per-document budget than comparison/extraction since a report can
# combine up to 5 documents -- keeps the combined prompt from ballooning.
REPORT_MAX_CHARS_PER_DOCUMENT = 6000

_REPORT_SYSTEM_PROMPT = (
    "You synthesize a report from one or more documents. Use ONLY what the "
    "excerpts actually say -- never invent a finding, risk, or recommendation "
    "not grounded in the text. If a focus area is given, emphasize it, but "
    "don't ignore other material findings. Respond with ONLY a JSON object, "
    'nothing else: {"title": "<short report title>", "overview": "<2-3 '
    'sentence overview>", "key_findings": ["..."], "risks_or_gaps": ["..."], '
    '"recommendations": ["..."]}. Each list item is a short, specific '
    "sentence. Leave a list empty rather than forcing an entry that isn't "
    "actually supported by the text."
)


def _parse_report(raw: str) -> dict | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return {
            "title": str(data["title"]),
            "overview": str(data["overview"]),
            "key_findings": [str(item) for item in data.get("key_findings", [])],
            "risks_or_gaps": [str(item) for item in data.get("risks_or_gaps", [])],
            "recommendations": [str(item) for item in data.get("recommendations", [])],
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


async def generate_report(
    db: AsyncSession, organization_id: uuid.UUID, document_ids: list[uuid.UUID], focus: str | None
) -> ReportResult:
    documents_text: list[tuple[Document, str, bool]] = []
    for document_id in document_ids:
        document, text = await _load_document_text(db, organization_id, document_id)
        text, truncated = _truncate(text, limit=REPORT_MAX_CHARS_PER_DOCUMENT)
        documents_text.append((document, text, truncated))

    any_truncated = any(truncated for _doc, _text, truncated in documents_text)
    blocks = "\n\n".join(
        f"Document: {doc.filename}{' [truncated]' if truncated else ''}\n{text}"
        for doc, text, truncated in documents_text
    )
    prompt = blocks if not focus else f"Focus area: {focus}\n\n{blocks}"

    try:
        provider = get_llm_provider()
        raw = provider.generate(_REPORT_SYSTEM_PROMPT, prompt)
    except LLMNotConfiguredError as exc:
        raise ReportUnavailableError(str(exc)) from exc
    except LLMGenerationError as exc:
        raise ReportUnavailableError(str(exc)) from exc

    parsed = _parse_report(raw)
    if parsed is None:
        raise ReportUnavailableError("The AI provider returned a response that couldn't be parsed")

    return ReportResult(
        documents=[doc.filename for doc, _text, _truncated in documents_text],
        truncated=any_truncated,
        **parsed,
    )
