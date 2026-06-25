from __future__ import annotations

from agent_memory.context.interface import MemoryContextRequest
from agent_memory.context.interface import MemoryContextResult
from agent_memory.long_term.decision import DecisionMemory
from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.procedural import WorkflowMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.store import MemoryStore


DEFAULT_TYPE_HEADINGS = {
    "semantic": "Known facts",
    "entity": "Known entities",
    "episodic": "Relevant events",
    "procedural": "Known procedures",
    "preference": "Known preferences",
    "decision": "Known decisions",
}


class LongTermMemoryContextBuilder:
    def __init__(
        self,
        memory_store: MemoryStore,
        heading: str = "Relevant long-term memory",
        type_headings: dict[str, str] | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._heading = heading
        self._type_headings = {
            **DEFAULT_TYPE_HEADINGS,
            **(type_headings or {}),
        }

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
            content=format_grouped_records(
                records,
                heading=self._heading,
                type_headings=self._type_headings,
            ),
            record_ids=[record.id for record in records],
        )


def format_grouped_records(
    records: list[LongTermRecord],
    heading: str = "Relevant long-term memory",
    type_headings: dict[str, str] | None = None,
) -> str:
    resolved_type_headings = {
        **DEFAULT_TYPE_HEADINGS,
        **(type_headings or {}),
    }
    lines = [f"{heading}:"]

    for memory_type, grouped_records in group_records_by_type(records).items():
        lines.append("")
        lines.append(f"{resolved_type_headings.get(memory_type, memory_type.title())}:")

        for record in grouped_records:
            lines.append(f"- {format_record(record)}")

    return "\n".join(lines)


def group_records_by_type(
    records: list[LongTermRecord],
) -> dict[str, list[LongTermRecord]]:
    grouped_records: dict[str, list[LongTermRecord]] = {}

    for record in records:
        grouped_records.setdefault(record.memory_type, []).append(record)

    return grouped_records


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

    if isinstance(record, PreferenceMemory):
        return f"{record.subject}: {record.preference}"

    if isinstance(record, DecisionMemory):
        result = f"{record.decision}"
        if record.rationale:
            result += f" Reason: {record.rationale}."
        if record.outcome:
            result += f" Outcome: {record.outcome}."
        return result

    return f"{record.key}: {record.metadata}"
