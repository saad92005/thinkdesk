import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider
from app.intelligence.schemas import ComparisonResult
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


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_CHARS_PER_DOCUMENT:
        return text, False
    return text[:MAX_CHARS_PER_DOCUMENT], True


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
