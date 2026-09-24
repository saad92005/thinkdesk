import re
import uuid

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


async def _load_org_chunks(db: AsyncSession, organization_id: uuid.UUID) -> list[DocumentChunk]:
    """Fetch this org's chunks. Filtering by organization_id here -- not
    trusting the caller to have already scoped the data -- is the tenant
    boundary for retrieval."""
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.organization_id == organization_id))
    return list(result.scalars().all())


async def cosine_similarity_search(
    db: AsyncSession, organization_id: uuid.UUID, query_embedding: list[float], top_k: int = 5
) -> list[tuple[DocumentChunk, float]]:
    """Pure-Python fallback ranking: fetch this org's chunks and rank by
    cosine similarity in-process.

    Fine for the chunk volumes a single organization has in V1. Swapping
    to a native pgvector column + HNSW index later changes this function's
    body, not its signature or callers -- see
    backend/vendor/pgvector-win64/README.md for that upgrade path.
    """
    chunks = await _load_org_chunks(db, organization_id)
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


def _bm25_rank(chunks: list[DocumentChunk], query: str) -> list[tuple[DocumentChunk, float]]:
    """Keyword ranking over this org's chunks. Catches exact terms
    (names, codes, numbers) that a semantic embedding can blur together --
    complementary to, not a replacement for, vector search."""
    corpus = [_tokenize(chunk.text) for chunk in chunks]
    query_tokens = _tokenize(query)
    if not query_tokens or not any(corpus):
        return [(chunk, 0.0) for chunk in chunks]

    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_tokens)
    return list(zip(chunks, (float(s) for s in scores)))


def _reciprocal_rank_fusion(
    rankings: list[list[tuple[DocumentChunk, float]]], top_k: int, k: int = 60
) -> list[tuple[DocumentChunk, float]]:
    """Combine multiple rankings of the same chunks by rank position
    (Reciprocal Rank Fusion), not raw score -- BM25 and cosine scores live
    on incomparable scales, but rank position is always comparable."""
    fused: dict[uuid.UUID, float] = {}
    by_id: dict[uuid.UUID, DocumentChunk] = {}

    for ranking in rankings:
        ordered = sorted(ranking, key=lambda pair: pair[1], reverse=True)
        for rank, (chunk, _score) in enumerate(ordered):
            by_id[chunk.id] = chunk
            fused[chunk.id] = fused.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)

    ranked_ids = sorted(fused.items(), key=lambda pair: pair[1], reverse=True)[:top_k]
    return [(by_id[chunk_id], score) for chunk_id, score in ranked_ids]


async def hybrid_search(
    db: AsyncSession,
    organization_id: uuid.UUID,
    query: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[tuple[DocumentChunk, float]]:
    """Vector similarity + BM25 keyword search, fused with Reciprocal Rank
    Fusion. Falls back gracefully to whichever signal has data -- an org
    with chunks but an empty/degenerate query still gets vector-only
    results rather than an error.
    """
    chunks = await _load_org_chunks(db, organization_id)
    if not chunks:
        return []

    vector_ranking = await cosine_similarity_search(db, organization_id, query_embedding, top_k=len(chunks))
    keyword_ranking = _bm25_rank(chunks, query)

    fused = _reciprocal_rank_fusion([vector_ranking, keyword_ranking], top_k=top_k)
    return fused
