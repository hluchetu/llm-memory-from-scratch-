from __future__ import annotations

from typing import Protocol

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult


class MemoryRetriever(Protocol):
    def add(self, record: LongTermRecord) -> None:
        ...

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        ...

    def delete(self, record_id: str) -> None:
        ...
