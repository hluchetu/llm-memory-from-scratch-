from __future__ import annotations

from agent_memory.context.interface import MemoryContextRequest
from agent_memory.context.interface import MemoryContextResult
from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.procedural import WorkflowMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.store import MemoryStore


class LongTermMemoryContextBuilder:
    def __init__(
        self,
        memory_store: MemoryStore,
        heading: str = "Relevant long-term memory",
    ) -> None:
        self._memory_store = memory_store
        self._heading = heading

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

        lines = [f"{self._heading}:"]

        for record in records:
            lines.append(f"- {format_record(record)}")

        return MemoryContextResult(
            content="\n".join(lines),
            record_ids=[record.id for record in records],
        )


def format_record(record: LongTermRecord) -> str:
    if isinstance(record, KnowledgeMemory):
        source = f" Source: {record.source}." if record.source else ""
        return f"{record.content}{source}"

    if isinstance(record, EntityMemory):
        return f"{record.name}: {record.description}"

    if isinstance(record, EventMemory):
        return f"{record.description} Occurred at: {record.occurred_at.isoformat()}."

    if isinstance(record, WorkflowMemory):
        steps = "; ".join(record.steps)
        return f"{record.key}: {steps}"

    return f"{record.key}: {record.metadata}"
