import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk


async def cosine_similarity_search(
    db: AsyncSession, organization_id: uuid.UUID, query_embedding: list[float], top_k: int = 5
) -> list[tuple[DocumentChunk, float]]:
    """Pure-Python fallback ranking: fetch this org's chunks (already
    filtered by organization_id -- the tenant boundary is enforced here,
    at the query, not by trusting the caller) and rank by cosine
    similarity in-process.

    Fine for the chunk volumes a single organization has in V1. Swapping
    to a native pgvector column + HNSW index later changes this function's
    body, not its signature or callers -- see
    backend/vendor/pgvector-win64/README.md for that upgrade path.
    """
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.organization_id == organization_id))
    chunks = result.scalars().all()
    if not chunks:
        return []

    query_vec = np.array(query_embedding)
    query_norm = float(np.linalg.norm(query_vec)) or 1.0

    scored: list[tuple[DocumentChunk, float]] = []
    for chunk in chunks:
        vec = np.array(chunk.embedding)
        denom = (float(np.linalg.norm(vec)) * query_norm) or 1.0
        score = float(np.dot(vec, query_vec) / denom)
        scored.append((chunk, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]
