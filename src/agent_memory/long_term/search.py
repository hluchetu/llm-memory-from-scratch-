from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from agent_memory.long_term.episodic.event import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType


@dataclass(frozen=True, kw_only=True)
class MetadataFilter:
    equals: dict[str, Any] = field(default_factory=dict)
    contains_all_tags: set[str] = field(default_factory=set)
    created_after: datetime | None = None
    created_before: datetime | None = None
    occurred_after: datetime | None = None
    occurred_before: datetime | None = None

    def matches(self, record: LongTermRecord) -> bool:
        for key, expected_value in self.equals.items():
            if record.metadata.get(key) != expected_value:
                return False

        if self.contains_all_tags:
            raw_tags = record.metadata.get("tags", [])
            tags = set(raw_tags) if isinstance(raw_tags, (list, set, tuple)) else set()

            if not self.contains_all_tags.issubset(tags):
                return False

        if self.created_after is not None and record.created_at < self.created_after:
            return False

        if self.created_before is not None and record.created_at > self.created_before:
            return False

        if self.occurred_after is not None:
            if not isinstance(record, EventMemory):
                return False

            if record.occurred_at < self.occurred_after:
                return False

        if self.occurred_before is not None:
            if not isinstance(record, EventMemory):
                return False

            if record.occurred_at > self.occurred_before:
                return False

        return True


@dataclass(frozen=True, kw_only=True)
class MemorySearch:
    namespace: tuple[str, ...]
    query: str
    memory_type: MemoryType | None = None
    limit: int = 5
    metadata: MetadataFilter = field(default_factory=MetadataFilter)


@dataclass(frozen=True, kw_only=True)
class RetrievalResult:
    record_id: str
    source: str
    score: float
    relevance_score: float | None = None
    recency_score: float | None = None
    importance_score: float | None = None
    reason: str | None = None
