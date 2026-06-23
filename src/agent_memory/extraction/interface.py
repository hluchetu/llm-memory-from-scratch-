from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_memory.long_term.item import LongTermRecord
from agent_memory.short_term.conversation.state import ConversationState


@dataclass(frozen=True, kw_only=True)
class MemoryExtractionRequest:
    namespace: tuple[str, ...]
    conversation: ConversationState
    since_item_id: str | None = None
    max_items: int | None = None


@dataclass(frozen=True, kw_only=True)
class MemoryExtractionResult:
    records: list[LongTermRecord]
    source_item_ids: list[str]
    skipped_reason: str | None = None


class MemoryExtractor(Protocol):
    def extract(self, request: MemoryExtractionRequest) -> MemoryExtractionResult:
        ...
