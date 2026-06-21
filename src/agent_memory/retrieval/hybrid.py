from __future__ import annotations

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.retriever import MemoryRetriever


class HybridMemoryRetriever:
    def __init__(self, retrievers: list[MemoryRetriever]) -> None:
        self._retrievers = retrievers

    def add(self, record: LongTermRecord) -> None:
        for retriever in self._retrievers:
            retriever.add(record)

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> list[str]:
        record_ids: list[str] = []
        seen_record_ids: set[str] = set()

        for retriever in self._retrievers:
            retrieved_ids = retriever.search(
                namespace=namespace,
                query=query,
                memory_type=memory_type,
                limit=limit,
            )

            for record_id in retrieved_ids:
                if record_id in seen_record_ids:
                    continue

                record_ids.append(record_id)
                seen_record_ids.add(record_id)

                if len(record_ids) >= limit:
                    return record_ids

        return record_ids

    def delete(self, record_id: str) -> None:
        for retriever in self._retrievers:
            retriever.delete(record_id)
