"""Vector store — ChromaDB-backed document storage and retrieval."""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


@dataclass
class SearchResult:
    text: str
    file_id: int
    title: str
    department: str
    date: str
    chunk_index: int
    heading: str
    score: float


class VectorStore(ABC):
    """Abstract interface for vector storage and search."""

    @abstractmethod
    def add_chunks(self, chunks: list[dict]) -> int:
        """Add chunks to vector store. Each chunk has 'id', 'text', 'embedding', 'metadata'. Returns count added."""
        ...

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int = 30) -> list[SearchResult]:
        """Search for most relevant chunks by embedding similarity."""
        ...

    @abstractmethod
    def delete_by_file_id(self, file_id: int) -> int:
        """Delete all chunks from a specific file. Returns count deleted."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Total number of chunks in the store."""
        ...


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str | None = None):
        self._client = chromadb.PersistentClient(
            path=persist_dir or settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="school_documents",
            metadata={"hnsw:space": "cosine"},
        )
        self._lock = threading.Lock()

    def add_chunks(self, chunks: list[dict]) -> int:
        if not chunks:
            return 0

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        embeddings = [c["embedding"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        with self._lock:
            self._collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        return len(chunks)

    def search(self, query_embedding: list[float], top_k: int = 30) -> list[SearchResult]:
        with self._lock:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = (results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else None) or {}
                search_results.append(SearchResult(
                    text=(results["documents"][0][i] or "") if results["documents"] and results["documents"][0] else "",
                    file_id=metadata.get("file_id", 0),
                    title=metadata.get("title", ""),
                    department=metadata.get("department", ""),
                    date=metadata.get("date", ""),
                    chunk_index=metadata.get("chunk_index", 0),
                    heading=metadata.get("heading", ""),
                    score=1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                ))

        return search_results

    def delete_by_file_id(self, file_id: int) -> int:
        """Delete all chunks for a given file_id."""
        with self._lock:
            results = self._collection.get(
                where={"file_id": file_id},
            )
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
        return len(results["ids"])

    def count(self) -> int:
        with self._lock:
            return self._collection.count()


# Singleton
vector_store: VectorStore = ChromaVectorStore()
