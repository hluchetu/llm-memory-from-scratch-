from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_memory.vector_store.interface import VectorSearchResult


class ChromaVectorStore:
    def __init__(
        self,
        path: str | Path | None = None,
        collection_name: str = "agent_memory",
    ) -> None:
        import chromadb

        if path is None:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(path=str(path))

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        record_id: str,
        vector: list[float],
        document: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._collection.upsert(
            ids=[record_id],
            embeddings=[vector],
            documents=[document],
            metadatas=[self._clean_metadata(metadata or {})],
        )

    def search(
        self,
        vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        if limit <= 0:
            return []

        result = self._collection.query(
            query_embeddings=[vector],
            n_results=limit,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        results: list[VectorSearchResult] = []

        for record_id, distance in zip(ids, distances):
            results.append(
                VectorSearchResult(
                    record_id=record_id,
                    score=1 - float(distance),
                )
            )

        return results

    def delete(self, record_id: str) -> None:
        self._collection.delete(ids=[record_id])

    def _clean_metadata(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, str | int | float | bool]:
        clean_metadata: dict[str, str | int | float | bool] = {}

        for key, value in metadata.items():
            if isinstance(value, str | int | float | bool):
                clean_metadata[key] = value
            elif isinstance(value, (list, tuple, set)):
                clean_metadata[key] = ",".join(str(item) for item in value)
            elif value is not None:
                clean_metadata[key] = str(value)

        return clean_metadata
