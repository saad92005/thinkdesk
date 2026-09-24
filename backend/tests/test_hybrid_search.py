import uuid

from app.models.chunk import DocumentChunk
from app.retrieval.vector_store import _bm25_rank, _reciprocal_rank_fusion, _tokenize


def make_chunk(text: str, embedding: list[float]) -> DocumentChunk:
    return DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        chunk_index=0,
        page_number=1,
        text=text,
        embedding=embedding,
    )


def test_tokenize_lowercases_and_strips_punctuation():
    assert _tokenize("Refund Policy: 30-Day Window!") == ["refund", "policy", "30", "day", "window"]


def test_bm25_rank_scores_matching_chunk_higher():
    exact = make_chunk("The refund policy allows returns within 30 days.", [0.0])
    unrelated_a = make_chunk("Our office is located in downtown Seattle.", [0.0])
    unrelated_b = make_chunk("Employees may take unlimited vacation days.", [0.0])

    scores = {
        chunk.text: score for chunk, score in _bm25_rank([unrelated_a, exact, unrelated_b], "refund policy")
    }

    assert scores[exact.text] > scores[unrelated_a.text]
    assert scores[exact.text] > scores[unrelated_b.text]


def test_bm25_rank_handles_empty_query_without_crashing():
    chunk = make_chunk("Some content.", [0.0])
    scores = _bm25_rank([chunk], "")
    assert scores == [(chunk, 0.0)]


def test_reciprocal_rank_fusion_promotes_item_ranked_high_in_both_lists():
    a = make_chunk("chunk a", [0.0])
    b = make_chunk("chunk b", [0.0])
    c = make_chunk("chunk c", [0.0])

    vector_ranking = [(a, 0.9), (b, 0.5), (c, 0.1)]
    keyword_ranking = [(a, 5.0), (c, 1.0), (b, 0.0)]

    fused = _reciprocal_rank_fusion([vector_ranking, keyword_ranking], top_k=3)

    assert [chunk.text for chunk, _ in fused][0] == "chunk a"


def test_reciprocal_rank_fusion_respects_top_k():
    chunks = [make_chunk(f"chunk {i}", [0.0]) for i in range(5)]
    ranking = [(chunk, float(len(chunks) - i)) for i, chunk in enumerate(chunks)]

    fused = _reciprocal_rank_fusion([ranking], top_k=2)

    assert len(fused) == 2
