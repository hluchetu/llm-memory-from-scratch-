from __future__ import annotations

import math
from datetime import datetime
from datetime import timezone

from agent_memory.long_term.episodic.event import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.retrieval._matching import blend_importance
from agent_memory.retrieval._matching import record_matches_search
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score


class EpisodicMemoryRetriever:
    def __init__(self) -> None:
        self._records: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records[record.id] = record

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        typed_search = MemorySearch(
            namespace=search.namespace,
            query=search.query,
            memory_type=search.memory_type or "episodic",
            limit=search.limit,
            metadata=search.metadata,
        )
        scored_records: list[tuple[float, float, float, LongTermRecord]] = []

        for record in self._records.values():
            if not record_matches_search(record, typed_search):
                continue

            relevance_score = token_overlap_score(
                typed_search.query,
                [searchable_text(record)],
            )
            recency_score = normalize_timestamp_score(event_timestamp(record))
            score = (relevance_score + recency_score) / 2
            scored_records.append((score, relevance_score, recency_score, record))

        scored_records.sort(
            key=lambda scored_record: scored_record[0],
            reverse=True,
        )
        return [
            RetrievalResult(
                record_id=record.id,
                source="episodic",
                score=blend_importance(score, record),
                relevance_score=relevance_score,
                recency_score=recency_score,
                importance_score=record.importance,
                reason="matched event text and ranked by event recency",
            )
            for score, relevance_score, recency_score, record in scored_records[
                : typed_search.limit
            ]
        ]

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)


def event_timestamp(record: LongTermRecord) -> float:
    if isinstance(record, EventMemory):
        return record.occurred_at.timestamp()

    return record.created_at.timestamp()


def normalize_timestamp_score(timestamp: float) -> float:
    now = datetime.now(timezone.utc).timestamp()
    age_in_hours = max((now - timestamp) / 3600, 0)
    return math.exp(-0.01 * age_in_hours)
