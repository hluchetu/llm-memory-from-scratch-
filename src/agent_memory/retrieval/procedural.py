from __future__ import annotations

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.procedural.workflow import WorkflowMemory
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.retrieval._matching import record_matches_search
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score


class ProceduralMemoryRetriever:
    def __init__(self) -> None:
        self._records_by_id: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records_by_id[record.id] = record

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        search = MemorySearch(
            namespace=search.namespace,
            query=search.query,
            memory_type=search.memory_type or "procedural",
            limit=search.limit,
            metadata=search.metadata,
        )
        scored_records: list[tuple[float, LongTermRecord]] = []

        for record in self._records_by_id.values():
            if not record_matches_search(record, search):
                continue

            exact_key_match = record.key.lower() == search.query.lower()
            candidates = [record.key, searchable_text(record)]

            if isinstance(record, WorkflowMemory):
                candidates.extend(record.steps)

            score = (
                1.0 if exact_key_match else token_overlap_score(search.query, candidates)
            )

            if score <= 0:
                continue

            scored_records.append((score, record))

        scored_records.sort(key=lambda scored_record: scored_record[0], reverse=True)
        return [
            RetrievalResult(
                record_id=record.id,
                source="procedural",
                score=score,
                relevance_score=score,
                reason="matched workflow key or steps",
            )
            for score, record in scored_records[: search.limit]
        ]

    def delete(self, record_id: str) -> None:
        self._records_by_id.pop(record_id, None)
