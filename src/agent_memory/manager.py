from __future__ import annotations

from dataclasses import dataclass

from agent_memory.context.interface import MemoryContextResult
from agent_memory.context.long_term import format_record
from agent_memory.extraction.interface import MemoryExtractionRequest
from agent_memory.extraction.interface import MemoryExtractionResult
from agent_memory.extraction.llm import LLMMemoryExtractor
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.store import MemoryStore
from agent_memory.short_term.conversation.state import ConversationState


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
    ) -> None:
        if not stores:
            raise ValueError("MemoryManager requires at least one store.")
        self._stores = stores
        self._extractor = extractor

    def inject(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
    ) -> MemoryContextResult:
        seen_ids: set[str] = set()
        records: list[LongTermRecord] = []

        for config in self._stores:
            for record in config.store.search(namespace=namespace, query=query, limit=limit):
                if record.id not in seen_ids:
                    seen_ids.add(record.id)
                    records.append(record)

        if not records:
            return MemoryContextResult(content="", record_ids=[])

        lines = ["Relevant memory:"]
        for record in records[:limit]:
            lines.append(f"- {format_record(record)}")

        return MemoryContextResult(
            content="\n".join(lines),
            record_ids=[record.id for record in records[:limit]],
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

        return result

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
            for record in config.store.search(namespace=namespace, query=query, limit=limit):
                if record.id not in seen_ids:
                    seen_ids.add(record.id)
                    records.append(record)

        return records[:limit]

    @property
    def store_descriptions(self) -> dict[str, str]:
        return {config.name: config.description for config in self._stores}
