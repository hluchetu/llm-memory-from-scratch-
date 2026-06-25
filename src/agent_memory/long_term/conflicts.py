from __future__ import annotations

from collections.abc import Iterable

from agent_memory.long_term.decision import DecisionMemory
from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.procedural import WorkflowMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory


def find_conflicting_records(
    new_record: LongTermRecord,
    candidates: Iterable[LongTermRecord],
) -> list[LongTermRecord]:
    conflicts: list[LongTermRecord] = []

    for candidate in candidates:
        if candidate.id == new_record.id:
            continue

        if candidate.invalidated_at is not None:
            continue

        if candidate.namespace != new_record.namespace:
            continue

        if candidate.memory_type != new_record.memory_type:
            continue

        if records_conflict(candidate, new_record):
            conflicts.append(candidate)

    return conflicts


def records_conflict(
    existing_record: LongTermRecord,
    new_record: LongTermRecord,
) -> bool:
    if existing_record.key == new_record.key:
        return record_fingerprint(existing_record) != record_fingerprint(new_record)

    if isinstance(existing_record, PreferenceMemory) and isinstance(
        new_record, PreferenceMemory
    ):
        return (
            normalize(existing_record.subject) == normalize(new_record.subject)
            and normalize(existing_record.preference) != normalize(new_record.preference)
        )

    if isinstance(existing_record, EntityMemory) and isinstance(new_record, EntityMemory):
        return (
            normalize(existing_record.name) == normalize(new_record.name)
            and normalize(existing_record.description)
            != normalize(new_record.description)
        )

    return False


def record_fingerprint(record: LongTermRecord) -> tuple[object, ...]:
    if isinstance(record, KnowledgeMemory):
        return (normalize(record.content), normalize(record.source or ""))

    if isinstance(record, EntityMemory):
        return (normalize(record.name), normalize(record.description))

    if isinstance(record, EventMemory):
        return (normalize(record.description), record.occurred_at)

    if isinstance(record, WorkflowMemory):
        return tuple(normalize(step) for step in record.steps)

    if isinstance(record, PreferenceMemory):
        return (normalize(record.subject), normalize(record.preference))

    if isinstance(record, DecisionMemory):
        return (
            normalize(record.decision),
            normalize(record.rationale or ""),
            normalize(record.outcome or ""),
        )

    return (normalize(record.key),)


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())
