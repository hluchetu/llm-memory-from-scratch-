from __future__ import annotations

from typing import Protocol

from agent_memory.short_term.conversation.state import ConversationState


class ExtractionTrigger(Protocol):
    def should_extract(self, conversation: ConversationState) -> bool:
        ...


class InvocationTrigger:
    """Extracts on every call."""

    def should_extract(self, conversation: ConversationState) -> bool:
        return True


class IntervalTrigger:
    """Extracts every N calls."""

    def __init__(self, every: int) -> None:
        if every < 1:
            raise ValueError("every must be at least 1")
        self._every = every
        self._call_count = 0

    def should_extract(self, conversation: ConversationState) -> bool:
        self._call_count += 1
        return self._call_count % self._every == 0
