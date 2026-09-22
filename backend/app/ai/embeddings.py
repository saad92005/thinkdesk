from abc import ABC, abstractmethod
from functools import lru_cache


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingProvider(EmbeddingProvider):
    """Runs entirely on this machine via ONNX (fastembed) -- no API key,
    no per-call cost. Swappable for an OpenAI/Cohere embedding provider
    later via get_embedding_provider() without touching call sites."""

    _MODEL_NAME = "BAAI/bge-small-en-v1.5"
    dimensions = 384

    def __init__(self) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=self._MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return LocalEmbeddingProvider()
