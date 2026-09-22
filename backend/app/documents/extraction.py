from pypdf import PdfReader


def extract_pages(file_path: str) -> list[str]:
    """Returns one string per page. Text-based PDFs only for V1 -- a
    scanned/image-only PDF will yield empty strings per page (no OCR yet)."""
    reader = PdfReader(file_path)
    return [page.extract_text() or "" for page in reader.pages]
