from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from datetime import timezone

from agent_memory.long_term.decision.decision import DecisionMemory
from agent_memory.long_term.episodic.event import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.preference.preference import PreferenceMemory
from agent_memory.long_term.procedural.workflow import WorkflowMemory
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.semantic.entity import EntityMemory
from agent_memory.long_term.semantic.knowledge import KnowledgeMemory


def namespace_matches(
    item_namespace: tuple[str, ...],
    search_namespace: tuple[str, ...],
) -> bool:
    return item_namespace[: len(search_namespace)] == search_namespace


def memory_type_matches(
    record: LongTermRecord,
    memory_type: MemoryType | None,
) -> bool:
    return memory_type is None or record.memory_type == memory_type


def record_matches_search(record: LongTermRecord, search: MemorySearch) -> bool:
    return (
        record_is_active(record)
        and namespace_matches(record.namespace, search.namespace)
        and memory_type_matches(record, search.memory_type)
        and search.metadata.matches(record)
    )


def record_is_active(
    record: LongTermRecord,
    current_time: datetime | None = None,
) -> bool:
    now = current_time or datetime.now(timezone.utc)

    if record.invalidated_at is not None:
        return False

    return record.expires_at is None or record.expires_at > now


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


IMPORTANCE_WEIGHT = 0.3


def importance_boost(record: LongTermRecord) -> float:
    if record.importance is None:
        return 0.0
    return record.importance * IMPORTANCE_WEIGHT


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def token_overlap_score(query: str, candidates: Iterable[str]) -> float:
    query_tokens = tokenize(query)

    if not query_tokens:
        return 0.0

    candidate_tokens: set[str] = set()

    for candidate in candidates:
        candidate_tokens.update(tokenize(candidate))

    if not candidate_tokens:
        return 0.0

    overlap = query_tokens.intersection(candidate_tokens)
    return len(overlap) / len(query_tokens)
