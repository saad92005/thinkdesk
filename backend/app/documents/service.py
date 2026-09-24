import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import get_embedding_provider
from app.database import async_session_factory
from app.documents.chunking import chunk_pages
from app.documents.extraction import extract_pages
from app.documents.storage import delete_upload, save_upload
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.models.user import User

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf"}


class UnsupportedFileTypeError(Exception):
    pass


class InvalidFileError(Exception):
    pass


async def create_document(
    db: AsyncSession,
    organization_id: uuid.UUID,
    uploader: User,
    filename: str,
    content_type: str,
    content: bytes,
) -> Document:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(content_type)
    if len(content) == 0:
        raise InvalidFileError("Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise InvalidFileError("File exceeds the 20MB limit")

    document = Document(
        organization_id=organization_id,
        uploaded_by_user_id=uploader.id,
        filename=filename,
        storage_path="",
        content_type=content_type,
        size_bytes=len(content),
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    await db.flush()

    document.storage_path = save_upload(organization_id, document.id, content)
    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession, organization_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.organization_id == organization_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
    return await db.scalar(
        select(Document).where(Document.id == document_id, Document.organization_id == organization_id)
    )


async def delete_document(db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID) -> bool:
    """Deletes the document row (its chunks cascade via the FK's
    ON DELETE CASCADE) and its file on disk. Returns False if the document
    doesn't exist in this organization, so the caller can 404 rather than
    silently succeeding on someone else's document."""
    document = await get_document(db, organization_id, document_id)
    if document is None:
        return False

    delete_upload(document.storage_path)
    await db.delete(document)
    await db.commit()
    return True


async def process_document(document_id: uuid.UUID) -> None:
    """Runs as a FastAPI BackgroundTask after the upload response has
    already been sent, so a large PDF never blocks the HTTP request.
    Opens its own DB session since the request's session is closed by the
    time this runs.

    V1 scale note: BackgroundTasks run in-process. If upload volume grows
    enough to need a real job queue (Celery/Redis), this function's body
    moves into a task with the same signature -- the API contract (upload
    now, poll document.status) doesn't change.
    """
    async with async_session_factory() as db:
        document = await db.get(Document, document_id)
        if document is None:
            return

        document.status = DocumentStatus.PROCESSING
        await db.commit()

        try:
            pages = extract_pages(document.storage_path)
            document.page_count = len(pages)

            chunks = chunk_pages(pages)
            if not chunks:
                raise ValueError(
                    "No extractable text found in this PDF. It may be a scanned "
                    "image without OCR, which isn't supported yet."
                )

            provider = get_embedding_provider()
            embeddings = provider.embed([chunk.text for chunk in chunks])

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        organization_id=document.organization_id,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        embedding=embedding,
                    )
                )

            document.status = DocumentStatus.READY
            await db.commit()
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)[:2000]
            await db.commit()
