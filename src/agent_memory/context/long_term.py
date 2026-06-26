from __future__ import annotations

from agent_memory.context.formatters import DEFAULT_TYPE_HEADINGS
from agent_memory.context.formatters import GroupedFormatter
from agent_memory.context.formatters import MemoryFormatter
from agent_memory.context.formatters import format_grouped_records
from agent_memory.context.formatters import format_record
from agent_memory.context.formatters import group_records_by_type
from agent_memory.context.interface import MemoryContextRequest
from agent_memory.context.interface import MemoryContextResult
from agent_memory.long_term.store import MemoryStore
from agent_memory.utils.asyncio import run_sync


__all__ = [
    "DEFAULT_TYPE_HEADINGS",
    "LongTermMemoryContextBuilder",
    "format_grouped_records",
    "format_record",
    "group_records_by_type",
]


class LongTermMemoryContextBuilder:
    def __init__(
        self,
        memory_store: MemoryStore,
        heading: str = "Relevant long-term memory",
        type_headings: dict[str, str] | None = None,
        formatter: MemoryFormatter | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._formatter = formatter or GroupedFormatter(
            heading=heading,
            type_headings=type_headings,
        )

    def build(self, request: MemoryContextRequest) -> MemoryContextResult:
        records = self._memory_store.search(
            namespace=request.namespace,
            query=request.query,
            memory_type=request.memory_type,
            limit=request.limit,
            metadata=request.metadata,
        )

        if not records:
            return MemoryContextResult(
                content="",
                record_ids=[],
            )

        return MemoryContextResult(
            content=self._formatter.format(records),
            record_ids=[record.id for record in records],
        )

    async def build_async(
        self,
        request: MemoryContextRequest,
    ) -> MemoryContextResult:
        return await run_sync(self.build, request)
