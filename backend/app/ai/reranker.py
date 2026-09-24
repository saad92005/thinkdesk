from abc import ABC, abstractmethod
from functools import lru_cache


class RerankerProvider(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: list[str]) -> list[float]: ...


class LocalRerankerProvider(RerankerProvider):
    """Free, local cross-encoder reranking via fastembed -- no API key,
    runs entirely on this machine (one-time ~80MB model download, then
    cached). A cross-encoder scores (query, document) pairs jointly, which
    is more precise than comparing independently-computed embeddings, but
    too slow to run over every chunk -- so it's used to re-score a
    shortlist that hybrid search already narrowed down, not the whole
    corpus. Scores are unbounded relevance logits, not probabilities;
    only their relative order matters."""

    def __init__(self, model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2") -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name=model_name)

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        return list(self._model.rerank(query, documents))


@lru_cache
def get_reranker_provider() -> RerankerProvider:
    return LocalRerankerProvider()
