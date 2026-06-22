from __future__ import annotations

from datetime import datetime
from typing import Any

from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.procedural import WorkflowMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory


RecordPayload = dict[str, Any]


def record_to_dict(record: LongTermRecord) -> RecordPayload:
    payload: RecordPayload = {
        "id": record.id,
        "namespace": list(record.namespace),
        "key": record.key,
        "memory_type": record.memory_type,
        "created_at": record.created_at.isoformat(),
        "metadata": record.metadata,
    }

    if isinstance(record, KnowledgeMemory):
        payload["record_type"] = "knowledge"
        payload["content"] = record.content
        payload["source"] = record.source
        return payload

    if isinstance(record, EntityMemory):
        payload["record_type"] = "entity"
        payload["name"] = record.name
        payload["description"] = record.description
        return payload

    if isinstance(record, EventMemory):
        payload["record_type"] = "event"
        payload["description"] = record.description
        payload["occurred_at"] = record.occurred_at.isoformat()
        return payload

    if isinstance(record, WorkflowMemory):
        payload["record_type"] = "workflow"
        payload["steps"] = record.steps
        return payload

    raise TypeError(f"Unsupported long-term record type: {type(record).__name__}")


def record_from_dict(payload: RecordPayload) -> LongTermRecord:
    record_type = payload.get("record_type")

    if record_type is None:
        raise ValueError("Long-term record payload is missing record_type.")

    record_type = str(record_type)
    common_fields = {
        "id": str(payload["id"]),
        "namespace": tuple(payload["namespace"]),
        "key": str(payload["key"]),
        "created_at": parse_datetime(payload["created_at"]),
        "metadata": dict(payload.get("metadata") or {}),
    }

    if record_type == "knowledge":
        return KnowledgeMemory(
            **common_fields,
            content=str(payload["content"]),
            source=optional_string(payload.get("source")),
        )

    if record_type == "entity":
        return EntityMemory(
            **common_fields,
            name=str(payload["name"]),
            description=str(payload["description"]),
        )

    if record_type == "event":
        return EventMemory(
            **common_fields,
            description=str(payload["description"]),
            occurred_at=parse_datetime(payload["occurred_at"]),
        )

    if record_type == "workflow":
        return WorkflowMemory(
            **common_fields,
            steps=[str(step) for step in payload.get("steps") or []],
        )

    raise ValueError(f"Unsupported long-term record type: {record_type}")


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    return datetime.fromisoformat(str(value))


def optional_string(value: Any) -> str | None:
    if value is None:
        return None

    return str(value)
