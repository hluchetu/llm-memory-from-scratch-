from __future__ import annotations

from agent_memory.long_term.retriever import MemoryRetriever
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import MetadataFilter
from agent_memory.long_term.search import RetrievalResult
from agent_memory.long_term.storage import MemoryStorage


class MemoryStore:
    def __init__(
        self,
        storage: MemoryStorage,
        retrievers: list[MemoryRetriever] | None = None,
    ) -> None:
        self._storage = storage
        self._retrievers = retrievers or []

    def put(self, record: LongTermRecord) -> None:
        self._storage.put(record)

        for retriever in self._retrievers:
            retriever.add(record)

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> LongTermRecord | None:
        return self._storage.get(namespace, key)

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
        metadata: MetadataFilter | None = None,
    ) -> list[LongTermRecord]:
        search = MemorySearch(
            namespace=namespace,
            query=query,
            memory_type=memory_type,
            limit=limit,
            metadata=metadata or MetadataFilter(),
        )
        results_by_record_id: dict[str, RetrievalResult] = {}

        for retriever in self._retrievers:
            for result in retriever.search(search):
                current_result = results_by_record_id.get(result.record_id)

                if current_result is not None and current_result.score >= result.score:
                    continue

                results_by_record_id[result.record_id] = result

        results = sorted(
            results_by_record_id.values(),
            key=lambda result: result.score,
            reverse=True,
        )
        record_ids = [result.record_id for result in results[:limit]]

        return self._storage.get_many(record_ids)

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        record = self._storage.get(namespace, key)

        self._storage.delete(namespace, key)

        if record is None:
            return

        for retriever in self._retrievers:
            retriever.delete(record.id)
