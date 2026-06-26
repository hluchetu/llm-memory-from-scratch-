from __future__ import annotations

from dataclasses import dataclass

from agent_memory.context.formatters import format_grouped_records
from agent_memory.context.interface import MemoryContextResult
from agent_memory.extraction.interface import MemoryExtractionRequest
from agent_memory.extraction.interface import MemoryExtractionResult
from agent_memory.extraction.llm import LLMMemoryExtractor
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.store import MemoryStore
from agent_memory.reflection import MemoryReflector
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.utils.asyncio import run_sync


@dataclass
class MemoryStoreConfig:
    name: str
    description: str
    store: MemoryStore
    writable: bool = True


class MemoryManager:
    def __init__(
        self,
        stores: list[MemoryStoreConfig],
        extractor: LLMMemoryExtractor | None = None,
        reflector: MemoryReflector | None = None,
    ) -> None:
        if not stores:
            raise ValueError("MemoryManager requires at least one store.")
        self._stores = stores
        self._extractor = extractor
        self._reflector = reflector

    def inject(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
    ) -> MemoryContextResult:
        seen_ids: set[str] = set()
        records: list[LongTermRecord] = []

        for config in self._stores:
            for record in config.store.search(
                namespace=namespace, query=query, limit=limit
            ):
                if record.id not in seen_ids:
                    seen_ids.add(record.id)
                    records.append(record)

        if not records:
            return MemoryContextResult(content="", record_ids=[])

        return MemoryContextResult(
            content=format_grouped_records(
                records[:limit],
                heading="Relevant memory",
            ),
            record_ids=[record.id for record in records[:limit]],
        )

    async def inject_async(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
    ) -> MemoryContextResult:
        return await run_sync(
            self.inject,
            query=query,
            namespace=namespace,
            limit=limit,
        )

    def extract(
        self,
        conversation: ConversationState,
        namespace: tuple[str, ...],
        since_item_id: str | None = None,
    ) -> MemoryExtractionResult:
        if self._extractor is None:
            return MemoryExtractionResult(
                records=[],
                source_item_ids=[],
                skipped_reason="No extractor configured.",
            )

        primary_store = next(
            (config.store for config in self._stores if config.writable),
            None,
        )

        result = self._extractor.extract(
            MemoryExtractionRequest(
                namespace=namespace,
                conversation=conversation,
                since_item_id=since_item_id,
                memory_store=primary_store,
            )
        )

        for config in self._stores:
            if not config.writable:
                continue
            for record in result.records:
                config.store.put(record)
            for key in result.invalidated_keys:
                config.store.invalidate(namespace, key)

        if self._reflector is not None and result.records:
            self._reflector.observe(result.records, namespace)

        return result

    async def extract_async(
        self,
        conversation: ConversationState,
        namespace: tuple[str, ...],
        since_item_id: str | None = None,
    ) -> MemoryExtractionResult:
        return await run_sync(
            self.extract,
            conversation=conversation,
            namespace=namespace,
            since_item_id=since_item_id,
        )

    def search(
        self,
        query: str,
        namespace: tuple[str, ...],
        store_name: str | None = None,
        limit: int = 5,
    ) -> list[LongTermRecord]:
        if store_name is not None:
            config = next(
                (c for c in self._stores if c.name == store_name),
                None,
            )
            if config is None:
                return []
            return config.store.search(namespace=namespace, query=query, limit=limit)

        seen_ids: set[str] = set()
        records: list[LongTermRecord] = []

        for config in self._stores:
            for record in config.store.search(
                namespace=namespace, query=query, limit=limit
            ):
                if record.id not in seen_ids:
                    seen_ids.add(record.id)
                    records.append(record)

        return records[:limit]

    async def search_async(
        self,
        query: str,
        namespace: tuple[str, ...],
        store_name: str | None = None,
        limit: int = 5,
    ) -> list[LongTermRecord]:
        return await run_sync(
            self.search,
            query=query,
            namespace=namespace,
            store_name=store_name,
            limit=limit,
        )

    @property
    def store_descriptions(self) -> dict[str, str]:
        return {config.name: config.description for config in self._stores}
