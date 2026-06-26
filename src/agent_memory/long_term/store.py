from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from datetime import timezone

from agent_memory.errors import NamespaceAccessError
from agent_memory.long_term.conflicts import find_conflicting_records
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.policy import AllowAllNamespacePolicy
from agent_memory.long_term.policy import NamespacePolicy
from agent_memory.long_term.ranking import reciprocal_rank_score
from agent_memory.long_term.retriever import MemoryRetriever
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import MetadataFilter
from agent_memory.long_term.storage import MemoryStorage
from agent_memory.long_term.text import searchable_text
from agent_memory.utils.asyncio import run_sync


class MemoryStore:
    def __init__(
        self,
        storage: MemoryStorage,
        retrievers: list[MemoryRetriever] | None = None,
        max_related_ids: int = 3,
        namespace_policy: NamespacePolicy | None = None,
    ) -> None:
        self._storage = storage
        self._retrievers = retrievers or []
        self._max_related_ids = max_related_ids
        self._namespace_policy = namespace_policy or AllowAllNamespacePolicy()

    def put(self, record: LongTermRecord) -> None:
        self._enforce_write(record.namespace)
        self._invalidate_conflicts(record)
        record = self._with_related_ids(record)
        self._storage.put(record)
        self._add_reverse_links(record)

        for retriever in self._retrievers:
            retriever.add(record)

    async def put_async(self, record: LongTermRecord) -> None:
        return await run_sync(self.put, record)

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> LongTermRecord | None:
        self._enforce_read(namespace)
        return self._storage.get(namespace, key)

    async def get_async(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> LongTermRecord | None:
        return await run_sync(self.get, namespace, key)

    def list(
        self,
        namespace: tuple[str, ...],
        memory_type: MemoryType | None = None,
        include_invalidated: bool = False,
    ) -> list[LongTermRecord]:
        self._enforce_read(namespace)
        return self._storage.list(
            namespace=namespace,
            memory_type=memory_type,
            include_invalidated=include_invalidated,
        )

    async def list_async(
        self,
        namespace: tuple[str, ...],
        memory_type: MemoryType | None = None,
        include_invalidated: bool = False,
    ) -> list[LongTermRecord]:
        return await run_sync(
            self.list,
            namespace=namespace,
            memory_type=memory_type,
            include_invalidated=include_invalidated,
        )

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
        metadata: MetadataFilter | None = None,
    ) -> list[LongTermRecord]:
        self._enforce_read(namespace)
        return self._search_records(
            namespace=namespace,
            query=query,
            memory_type=memory_type,
            limit=limit,
            metadata=metadata,
        )

    def _search_records(
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
        rrf_scores_by_record_id: dict[str, float] = {}

        for retriever in self._retrievers:
            for rank, result in enumerate(retriever.search(search), start=1):
                rrf_scores_by_record_id[result.record_id] = (
                    rrf_scores_by_record_id.get(result.record_id, 0.0)
                    + reciprocal_rank_score(rank)
                )

        record_ids = sorted(
            rrf_scores_by_record_id,
            key=lambda record_id: rrf_scores_by_record_id[record_id],
            reverse=True,
        )[:limit]

        return self._storage.get_many(record_ids)

    async def search_async(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
        metadata: MetadataFilter | None = None,
    ) -> list[LongTermRecord]:
        return await run_sync(
            self.search,
            namespace=namespace,
            query=query,
            memory_type=memory_type,
            limit=limit,
            metadata=metadata,
        )

    def invalidate(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> bool:
        self._enforce_write(namespace)
        record = self._storage.get(namespace, key)

        if record is None or record.invalidated_at is not None:
            return False

        invalidated = replace(
            record,
            invalidated_at=datetime.now(timezone.utc),
        )
        self._storage.put(invalidated)

        for retriever in self._retrievers:
            retriever.delete(record.id)

        return True

    async def invalidate_async(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> bool:
        return await run_sync(self.invalidate, namespace, key)

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        self._enforce_write(namespace)
        record = self._storage.get(namespace, key)

        self._storage.delete(namespace, key)

        if record is None:
            return

        for retriever in self._retrievers:
            retriever.delete(record.id)

    async def delete_async(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        return await run_sync(self.delete, namespace, key)

    def _invalidate_conflicts(self, record: LongTermRecord) -> None:
        candidates = self._storage.list(
            namespace=record.namespace,
            memory_type=record.memory_type,
        )

        for stale_record in find_conflicting_records(record, candidates):
            invalidated = replace(
                stale_record,
                invalidated_at=datetime.now(timezone.utc),
            )
            self._storage.put(invalidated)

            for retriever in self._retrievers:
                retriever.delete(stale_record.id)

    def _with_related_ids(self, record: LongTermRecord) -> LongTermRecord:
        if self._max_related_ids <= 0:
            return record

        related_ids = [
            related_id
            for related_id in record.related_ids
            if related_id != record.id
        ]

        for related_record in self._search_records(
            namespace=record.namespace,
            query=searchable_text(record),
            limit=self._max_related_ids,
        ):
            if related_record.id == record.id:
                continue

            if related_record.id not in related_ids:
                related_ids.append(related_record.id)

        return replace(
            record,
            related_ids=tuple(related_ids[: self._max_related_ids]),
        )

    def _add_reverse_links(self, record: LongTermRecord) -> None:
        for related_id in record.related_ids:
            related_record = self._storage.get_by_id(related_id)

            if related_record is None:
                continue

            if related_record.invalidated_at is not None:
                continue

            if related_record.namespace != record.namespace:
                continue

            if record.id in related_record.related_ids:
                continue

            self._storage.put(
                replace(
                    related_record,
                    related_ids=(
                        record.id,
                        *related_record.related_ids,
                    )[: self._max_related_ids],
                )
            )

    def _enforce_read(self, namespace: tuple[str, ...]) -> None:
        if self._namespace_policy.can_read(namespace):
            return

        raise NamespaceAccessError(
            f"Read access denied for namespace: {format_namespace(namespace)}"
        )

    def _enforce_write(self, namespace: tuple[str, ...]) -> None:
        if self._namespace_policy.can_write(namespace):
            return

        raise NamespaceAccessError(
            f"Write access denied for namespace: {format_namespace(namespace)}"
        )


def format_namespace(namespace: tuple[str, ...]) -> str:
    return "/".join(namespace)
