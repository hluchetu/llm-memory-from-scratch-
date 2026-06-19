from __future__ import annotations

from typing import Protocol

from agent_memory.long_term.state import MemoryRecord


class LongTermMemoryStore(Protocol):
    def put(self, record: MemoryRecord) -> None:
        ...

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> MemoryRecord | None:
        ...

    def get_many(self, ids: list[str]) -> list[MemoryRecord]:
        ...

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        ...

