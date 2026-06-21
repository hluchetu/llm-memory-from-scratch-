from __future__ import annotations

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.procedural.workflow import WorkflowMemory
from agent_memory.retrieval._matching import namespace_matches
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score


class ProceduralMemoryRetriever:
    def __init__(self) -> None:
        self._records_by_id: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records_by_id[record.id] = record

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> list[str]:
        target_type: MemoryType = memory_type or "procedural"
        scored_records: list[tuple[float, LongTermRecord]] = []

        for record in self._records_by_id.values():
            if record.memory_type != target_type:
                continue

            if not namespace_matches(record.namespace, namespace):
                continue

            exact_key_match = record.key.lower() == query.lower()
            candidates = [record.key, searchable_text(record)]

            if isinstance(record, WorkflowMemory):
                candidates.extend(record.steps)

            score = 1.0 if exact_key_match else token_overlap_score(query, candidates)

            if score <= 0:
                continue

            scored_records.append((score, record))

        scored_records.sort(key=lambda scored_record: scored_record[0], reverse=True)
        return [record.id for _, record in scored_records[:limit]]

    def delete(self, record_id: str) -> None:
        self._records_by_id.pop(record_id, None)
