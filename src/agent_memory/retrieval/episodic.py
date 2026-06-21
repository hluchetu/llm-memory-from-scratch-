from __future__ import annotations

from agent_memory.long_term.episodic.event import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.retrieval._matching import namespace_matches
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score


class EpisodicMemoryRetriever:
    def __init__(self) -> None:
        self._records: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records[record.id] = record

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> list[str]:
        target_type: MemoryType = memory_type or "episodic"
        scored_records: list[tuple[float, float, LongTermRecord]] = []

        for record in self._records.values():
            if record.memory_type != target_type:
                continue

            if not namespace_matches(record.namespace, namespace):
                continue

            score = token_overlap_score(query, [searchable_text(record)])
            recency_score = event_timestamp(record)
            scored_records.append((score, recency_score, record))

        scored_records.sort(
            key=lambda scored_record: (scored_record[0], scored_record[1]),
            reverse=True,
        )
        return [record.id for _, _, record in scored_records[:limit]]

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)


def event_timestamp(record: LongTermRecord) -> float:
    if isinstance(record, EventMemory):
        return record.occurred_at.timestamp()

    return record.created_at.timestamp()
