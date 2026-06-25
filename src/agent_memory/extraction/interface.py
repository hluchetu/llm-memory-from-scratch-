from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Protocol

from agent_memory.long_term.item import LongTermRecord
from agent_memory.short_term.conversation.state import ConversationState

if TYPE_CHECKING:
    from agent_memory.long_term.store import MemoryStore


@dataclass(frozen=True, kw_only=True)
class MemoryExtractionRequest:
    namespace: tuple[str, ...]
    conversation: ConversationState
    since_item_id: str | None = None
    max_items: int | None = None
    memory_store: MemoryStore | None = None


@dataclass(frozen=True, kw_only=True)
class MemoryExtractionResult:
    records: list[LongTermRecord]
    source_item_ids: list[str]
    invalidated_keys: list[str] = field(default_factory=list)
    skipped_reason: str | None = None


class MemoryExtractor(Protocol):
    def extract(self, request: MemoryExtractionRequest) -> MemoryExtractionResult:
        ...
