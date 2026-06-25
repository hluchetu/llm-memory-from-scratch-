from __future__ import annotations

from typing import Protocol

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.retrieval._matching import importance_boost
from agent_memory.retrieval._matching import record_matches_search
from agent_memory.retrieval._matching import searchable_text
from agent_memory.vector_store import VectorStore


class TextEmbedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class SemanticMemoryRetriever:
    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._records: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        document = searchable_text(record)
        self._records[record.id] = record
        self._vector_store.upsert(
            record_id=record.id,
            vector=self._embedder.embed(document),
            document=document,
            metadata={
                "memory_type": record.memory_type,
                "namespace": "/".join(record.namespace),
                **record.metadata,
            },
        )

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        query_vector = self._embedder.embed(search.query)
        vector_results = self._vector_store.search(
            vector=query_vector,
            limit=max(search.limit * 10, search.limit),
        )
        retrieval_results: list[RetrievalResult] = []

        for vector_result in vector_results:
            record = self._records.get(vector_result.record_id)

            if record is None:
                continue

            if not record_matches_search(record, search):
                continue

            if vector_result.score <= 0:
                continue

            retrieval_results.append(
                RetrievalResult(
                    record_id=record.id,
                    source="semantic",
                    score=vector_result.score + importance_boost(record),
                    relevance_score=vector_result.score,
                    importance_score=record.importance,
                    reason="cosine similarity from Chroma vector search",
                )
            )

            if len(retrieval_results) >= search.limit:
                break

        return retrieval_results

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)
        self._vector_store.delete(record_id)
