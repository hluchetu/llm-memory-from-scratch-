from __future__ import annotations

from agent_memory.long_term.decision.decision import DecisionMemory
from agent_memory.long_term.episodic.event import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.preference.preference import PreferenceMemory
from agent_memory.long_term.procedural.workflow import WorkflowMemory
from agent_memory.long_term.semantic.entity import EntityMemory
from agent_memory.long_term.semantic.knowledge import KnowledgeMemory


def searchable_text(record: LongTermRecord) -> str:
    metadata_values = " ".join(str(value) for value in record.metadata.values())

    if isinstance(record, KnowledgeMemory):
        return f"{record.key} {record.content} {record.source or ''} {metadata_values}"

    if isinstance(record, EntityMemory):
        return f"{record.key} {record.name} {record.description} {metadata_values}"

    if isinstance(record, EventMemory):
        return (
            f"{record.key} {record.description} "
            f"{record.occurred_at.isoformat()} {metadata_values}"
        )

    if isinstance(record, WorkflowMemory):
        steps = " ".join(record.steps)
        return f"{record.key} {steps} {metadata_values}"

    if isinstance(record, PreferenceMemory):
        return f"{record.key} {record.subject} {record.preference} {metadata_values}"

    if isinstance(record, DecisionMemory):
        rationale = record.rationale or ""
        return f"{record.key} {record.decision} {rationale} {metadata_values}"

    return f"{record.key} {metadata_values}"
