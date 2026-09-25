import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import get_embedding_provider
from app.ai.reranker import get_reranker_provider
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.retrieval.query_rewrite import rewrite_query
from app.retrieval.schemas import SearchResultItem
from app.retrieval.vector_store import hybrid_search

# Retrieve a wider candidate pool than we return, then let the (more
# precise, but too slow to run over every chunk) cross-encoder reorder it.
# Costs nothing extra in DB round trips -- hybrid_search already scores
# every chunk in the org internally before truncating to a top-k.
CANDIDATE_POOL_MULTIPLIER = 4
MAX_CANDIDATES = 25


async def search(db: AsyncSession, organization_id: uuid.UUID, query: str, top_k: int) -> list[SearchResultItem]:
    provider = get_embedding_provider()
    candidate_k = min(top_k * CANDIDATE_POOL_MULTIPLIER, MAX_CANDIDATES)

    # Query rewriting widens recall: an LLM-generated alternate phrasing can
    # surface chunks sharing little vocabulary with the user's literal
    # wording. Each variant (original + rewrites) runs its own hybrid
    # search; results are merged by chunk id (best fusion score wins)
    # before reranking against the ORIGINAL query -- rewrites are a recall
    # tool, relevance is still judged against what the user actually asked.
    candidates_by_chunk: dict[uuid.UUID, tuple[DocumentChunk, float]] = {}
    for variant in rewrite_query(query):
        query_embedding = provider.embed([variant])[0]
        for chunk, score in await hybrid_search(db, organization_id, variant, query_embedding, candidate_k):
            existing = candidates_by_chunk.get(chunk.id)
            if existing is None or score > existing[1]:
                candidates_by_chunk[chunk.id] = (chunk, score)

    if not candidates_by_chunk:
        return []
    candidates = sorted(candidates_by_chunk.values(), key=lambda pair: pair[1], reverse=True)[:MAX_CANDIDATES]

    reranker = get_reranker_provider()
    rerank_scores = reranker.rerank(query, [chunk.text for chunk, _fusion_score in candidates])
    reranked = sorted(zip(candidates, rerank_scores), key=lambda pair: pair[1], reverse=True)[:top_k]

    results: list[SearchResultItem] = []
    for (chunk, _fusion_score), rerank_score in reranked:
        document = await db.get(Document, chunk.document_id)
        results.append(
            SearchResultItem(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=document.filename if document else "unknown",
                page_number=chunk.page_number,
                text=chunk.text,
                score=rerank_score,
            )
        )
    return results
