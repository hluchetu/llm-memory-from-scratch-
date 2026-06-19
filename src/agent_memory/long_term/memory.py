from __future__ import annotations

from agent_memory.long_term.retriever import MemoryRetriever
from agent_memory.long_term.state import MemoryRecord
from agent_memory.long_term.state import MemoryType
from agent_memory.long_term.store import LongTermMemoryStore


class LongTermMemory:
    def __init__(
        self,
        store: LongTermMemoryStore,
        retrievers: list[MemoryRetriever] | None = None,
    ) -> None:
        self._store = store
        self._retrievers = retrievers or []

    def put(self, record: MemoryRecord) -> None:
        self._store.put(record)

        for retriever in self._retrievers:
            retriever.add(record)

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> MemoryRecord | None:
        return self._store.get(namespace, key)

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        record_ids: list[str] = []
        seen_record_ids: set[str] = set()

        for retriever in self._retrievers:
            for record_id in retriever.search(
                namespace=namespace,
                query=query,
                memory_type=memory_type,
                limit=limit,
            ):
                if record_id in seen_record_ids:
                    continue

                record_ids.append(record_id)
                seen_record_ids.add(record_id)

                if len(record_ids) >= limit:
                    break

            if len(record_ids) >= limit:
                break

        return self._store.get_many(record_ids)

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        record = self._store.get(namespace, key)

        self._store.delete(namespace, key)

        if record is None:
            return

        for retriever in self._retrievers:
            retriever.delete(record.id)
