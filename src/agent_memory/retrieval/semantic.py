from __future__ import annotations

import math
from typing import Protocol

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.retrieval._matching import record_matches_search
from agent_memory.retrieval._matching import searchable_text


class TextEmbedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class SemanticMemoryRetriever:
    def __init__(self, embedder: TextEmbedder) -> None:
        self._embedder = embedder
        self._records: dict[str, LongTermRecord] = {}
        self._vectors: dict[str, list[float]] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records[record.id] = record
        self._vectors[record.id] = self._embedder.embed(searchable_text(record))

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        query_vector = self._embedder.embed(search.query)
        scored_records: list[tuple[float, LongTermRecord]] = []

        for record in self._records.values():
            if not record_matches_search(record, search):
                continue

            record_vector = self._vectors.get(record.id)

            if record_vector is None:
                continue

            score = cosine_similarity(query_vector, record_vector)

            if score <= 0:
                continue

            scored_records.append((score, record))

        scored_records.sort(key=lambda scored_record: scored_record[0], reverse=True)
        return [
            RetrievalResult(
                record_id=record.id,
                source="semantic",
                score=score,
                relevance_score=score,
                reason="cosine similarity between query and record embeddings",
            )
            for score, record in scored_records[: search.limit]
        ]

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)
        self._vectors.pop(record_id, None)


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(value * value for value in vector_a))
    norm_b = math.sqrt(sum(value * value for value in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)
