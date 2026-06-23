from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_memory.long_term.item import MemoryType
from agent_memory.long_term.search import MetadataFilter


@dataclass(frozen=True, kw_only=True)
class MemoryContextRequest:
    namespace: tuple[str, ...]
    query: str
    memory_type: MemoryType | None = None
    limit: int = 5
    metadata: MetadataFilter | None = None


@dataclass(frozen=True, kw_only=True)
class MemoryContextResult:
    content: str
    record_ids: list[str]

    @property
    def has_content(self) -> bool:
        return bool(self.content.strip())


class MemoryContextBuilder(Protocol):
    def build(self, request: MemoryContextRequest) -> MemoryContextResult:
        ...
