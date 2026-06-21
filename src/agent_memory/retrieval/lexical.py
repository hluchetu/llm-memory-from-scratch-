from __future__ import annotations

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.retrieval._matching import memory_type_matches
from agent_memory.retrieval._matching import namespace_matches
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score


class LexicalMemoryRetriever:
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
        scored_records: list[tuple[float, LongTermRecord]] = []

        for record in self._records.values():
            if not namespace_matches(record.namespace, namespace):
                continue

            if not memory_type_matches(record, memory_type):
                continue

            score = token_overlap_score(query, [searchable_text(record)])

            if score <= 0:
                continue

            scored_records.append((score, record))

        scored_records.sort(key=lambda scored_record: scored_record[0], reverse=True)
        return [record.id for _, record in scored_records[:limit]]

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)
