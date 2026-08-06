"""Embedding service — generates vector representations of text using BGE-M3 or bge-small-zh."""

from abc import ABC, abstractmethod

from app.core.config import settings


class EmbedderService(ABC):
    """Abstract interface for text embedding."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string. Returns a vector."""
        ...


class LocalSentenceTransformerEmbedder(EmbedderService):
    """Loads a sentence-transformers model locally for embedding."""

    def __init__(self, model_name: str | None = None, device: str | None = None):
        self._model_name = model_name or settings.embedding_model
        self._device = device or settings.embedding_device
        self._model = None  # lazy load

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        vector = self.model.encode(
            [query],
            normalize_embeddings=True,
        )
        return vector[0].tolist()


# Singleton
embedder: EmbedderService = LocalSentenceTransformerEmbedder()
