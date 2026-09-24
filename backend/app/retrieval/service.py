import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import get_embedding_provider
from app.models.document import Document
from app.retrieval.schemas import SearchResultItem
from app.retrieval.vector_store import hybrid_search


async def search(db: AsyncSession, organization_id: uuid.UUID, query: str, top_k: int) -> list[SearchResultItem]:
    provider = get_embedding_provider()
    query_embedding = provider.embed([query])[0]
    scored = await hybrid_search(db, organization_id, query, query_embedding, top_k)

    results: list[SearchResultItem] = []
    for chunk, score in scored:
        document = await db.get(Document, chunk.document_id)
        results.append(
            SearchResultItem(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=document.filename if document else "unknown",
                page_number=chunk.page_number,
                text=chunk.text,
                score=score,
            )
        )
    return results
