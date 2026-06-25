from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from datetime import timezone

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.text import searchable_text


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


IMPORTANCE_WEIGHT = 0.3


def importance_boost(record: LongTermRecord) -> float:
    if record.importance is None:
        return 0.0
    return record.importance * IMPORTANCE_WEIGHT


def blend_importance(score: float, record: LongTermRecord) -> float:
    relevance = clamp_score(score)

    if record.importance is None:
        return relevance

    importance = clamp_score(record.importance)
    return clamp_score(
        relevance * (1 - IMPORTANCE_WEIGHT)
        + importance * IMPORTANCE_WEIGHT
    )


def clamp_score(score: float) -> float:
    return max(0.0, min(1.0, score))


def tokenize_terms(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def tokenize(text: str) -> set[str]:
    return set(tokenize_terms(text))


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
