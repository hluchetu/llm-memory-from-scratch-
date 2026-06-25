from __future__ import annotations

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.retrieval._matching import record_matches_search
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score
from agent_memory.retrieval._matching import importance_boost


class LexicalMemoryRetriever:
    def __init__(self) -> None:
        self._records: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records[record.id] = record

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        scored_records: list[tuple[float, LongTermRecord]] = []

        for record in self._records.values():
            if not record_matches_search(record, search):
                continue

            score = token_overlap_score(search.query, [searchable_text(record)])

            if score <= 0:
                continue

            scored_records.append((score, record))

        scored_records.sort(key=lambda scored_record: scored_record[0], reverse=True)
        return [
            RetrievalResult(
                record_id=record.id,
                source="lexical",
                score=score + importance_boost(record),
                relevance_score=score,
                importance_score=record.importance,
                reason="matched query tokens against record text",
            )
            for score, record in scored_records[: search.limit]
        ]

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)
