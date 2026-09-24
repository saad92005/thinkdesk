from app.ai.reranker import LocalRerankerProvider


def test_reranker_scores_relevant_document_higher():
    provider = LocalRerankerProvider()
    query = "What is the refund policy?"
    documents = [
        "Employees are entitled to unlimited paid vacation days per year.",
        "Customers may request a full refund within 30 days of purchase.",
    ]

    scores = provider.rerank(query, documents)

    assert len(scores) == 2
    assert scores[1] > scores[0]


def test_reranker_handles_empty_document_list():
    provider = LocalRerankerProvider()
    assert provider.rerank("anything", []) == []
