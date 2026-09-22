import re
from dataclasses import dataclass

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int


def _split_paragraphs(page_text: str) -> list[str]:
    return [p.strip() for p in page_text.split("\n\n") if p.strip()]


def _split_long_paragraph(paragraph: str, max_size: int) -> list[str]:
    """Break a paragraph that alone exceeds max_size, preferring sentence
    boundaries and falling back to a hard split only if a single sentence
    is still too long."""
    if len(paragraph) <= max_size:
        return [paragraph]

    sentences = _SENTENCE_BOUNDARY.split(paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > max_size:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)

    final: list[str] = []
    for piece in pieces:
        if len(piece) <= max_size:
            final.append(piece)
        else:
            final.extend(piece[i : i + max_size] for i in range(0, len(piece), max_size))
    return final


def chunk_pages(pages: list[str], chunk_size: int = 1000, chunk_overlap: int = 150) -> list[Chunk]:
    """Paragraph-aware chunking that keeps track of which page each chunk
    started on, so citations can point back to a real page number.

    Deliberately simple (paragraphs -> merge up to chunk_size -> carry a
    trailing overlap into the next chunk) rather than a heavier semantic
    chunker; configurable enough to tune without rewriting the pipeline.
    """
    chunks: list[Chunk] = []
    buffer = ""
    buffer_page: int | None = None
    chunk_index = 0

    def flush() -> None:
        nonlocal buffer, buffer_page, chunk_index
        if buffer.strip():
            assert buffer_page is not None
            chunks.append(Chunk(text=buffer.strip(), page_number=buffer_page, chunk_index=chunk_index))
            chunk_index += 1

    for page_number, page_text in enumerate(pages, start=1):
        for paragraph in _split_paragraphs(page_text):
            for piece in _split_long_paragraph(paragraph, chunk_size):
                if buffer_page is None:
                    buffer_page = page_number

                candidate = f"{buffer} {piece}".strip() if buffer else piece
                if buffer and len(candidate) > chunk_size:
                    flush()
                    overlap_text = buffer[-chunk_overlap:] if chunk_overlap else ""
                    buffer = f"{overlap_text} {piece}".strip()
                    buffer_page = page_number
                else:
                    buffer = candidate

    flush()
    return chunks
