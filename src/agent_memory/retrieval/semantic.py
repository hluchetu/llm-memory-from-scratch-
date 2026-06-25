from __future__ import annotations

from typing import Protocol

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.long_term.storage import MemoryStorage
from agent_memory.retrieval._matching import blend_importance
from agent_memory.retrieval._matching import clamp_score
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
        storage: MemoryStorage,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._storage = storage

    def add(self, record: LongTermRecord) -> None:
        document = searchable_text(record)
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
        results_by_record_id: dict[str, RetrievalResult] = {}

        for vector_result in vector_results:
            record = self._storage.get_by_id(vector_result.record_id)

            if record is None:
                continue

            if not record_matches_search(record, search):
                continue

            if vector_result.score <= 0:
                continue

            relevance_score = clamp_score(vector_result.score)
            results_by_record_id[record.id] = RetrievalResult(
                record_id=record.id,
                source="semantic",
                score=blend_importance(relevance_score, record),
                relevance_score=relevance_score,
                importance_score=record.importance,
                reason="cosine similarity from Chroma vector search",
            )
            self._add_related_results(
                parent_record=record,
                parent_relevance_score=relevance_score,
                search=search,
                results_by_record_id=results_by_record_id,
            )

            if len(results_by_record_id) >= search.limit:
                break

        retrieval_results = sorted(
            results_by_record_id.values(),
            key=lambda result: result.score,
            reverse=True,
        )
        return retrieval_results[: search.limit]

    def _add_related_results(
        self,
        parent_record: LongTermRecord,
        parent_relevance_score: float,
        search: MemorySearch,
        results_by_record_id: dict[str, RetrievalResult],
    ) -> None:
        related_relevance_score = parent_relevance_score * 0.9

        for related_id in parent_record.related_ids:
            if related_id in results_by_record_id:
                continue

            related_record = self._storage.get_by_id(related_id)

            if related_record is None:
                continue

            if not record_matches_search(related_record, search):
                continue

            results_by_record_id[related_record.id] = RetrievalResult(
                record_id=related_record.id,
                source="semantic",
                score=blend_importance(
                    related_relevance_score,
                    related_record,
                ),
                relevance_score=related_relevance_score,
                importance_score=related_record.importance,
                reason=(
                    "one-hop related memory from semantic match "
                    f"{parent_record.id}"
                )
            )

    def delete(self, record_id: str) -> None:
        self._vector_store.delete(record_id)
