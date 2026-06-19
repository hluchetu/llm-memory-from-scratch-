from __future__ import annotations

from typing import Protocol

from agent_memory.long_term.state import MemoryRecord
from agent_memory.long_term.state import MemoryType


class MemoryRetriever(Protocol):
    def add(self, record: MemoryRecord) -> None:
        ...

    def search(
        self,
        namespace: tuple[str, ...],
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> list[str]:
        ...

    def delete(self, record_id: str) -> None:
        ...
