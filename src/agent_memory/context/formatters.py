from __future__ import annotations

from html import escape
from typing import Protocol

from agent_memory.long_term.decision import DecisionMemory
from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.procedural import WorkflowMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory


DEFAULT_TYPE_HEADINGS = {
    "semantic": "Known facts",
    "entity": "Known entities",
    "episodic": "Relevant events",
    "procedural": "Known procedures",
    "preference": "Known preferences",
    "decision": "Known decisions",
}


class MemoryFormatter(Protocol):
    def format(self, records: list[LongTermRecord]) -> str:
        ...


class BulletListFormatter:
    def __init__(self, heading: str = "Relevant long-term memory") -> None:
        self._heading = heading

    def format(self, records: list[LongTermRecord]) -> str:
        lines = [f"{self._heading}:"]

        for record in records:
            lines.append(f"- {format_record(record)}")

        return "\n".join(lines)


class GroupedFormatter:
    def __init__(
        self,
        heading: str = "Relevant long-term memory",
        type_headings: dict[str, str] | None = None,
    ) -> None:
        self._heading = heading
        self._type_headings = {
            **DEFAULT_TYPE_HEADINGS,
            **(type_headings or {}),
        }

    def format(self, records: list[LongTermRecord]) -> str:
        lines = [f"{self._heading}:"]

        for memory_type, grouped_records in group_records_by_type(records).items():
            lines.append("")
            lines.append(f"{self._type_headings.get(memory_type, memory_type.title())}:")

            for record in grouped_records:
                lines.append(f"- {format_record(record)}")

        return "\n".join(lines)


class XMLBlockFormatter:
    def __init__(self, root_tag: str = "memory") -> None:
        self._root_tag = root_tag

    def format(self, records: list[LongTermRecord]) -> str:
        lines = [f"<{self._root_tag}>"]

        for record in records:
            lines.append(
                "  "
                f'<item id="{escape(record.id)}" '
                f'type="{escape(record.memory_type)}" '
                f'key="{escape(record.key)}">'
                f"{escape(format_record(record))}"
                "</item>"
            )

        lines.append(f"</{self._root_tag}>")
        return "\n".join(lines)


def format_grouped_records(
    records: list[LongTermRecord],
    heading: str = "Relevant long-term memory",
    type_headings: dict[str, str] | None = None,
) -> str:
    return GroupedFormatter(
        heading=heading,
        type_headings=type_headings,
    ).format(records)


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
