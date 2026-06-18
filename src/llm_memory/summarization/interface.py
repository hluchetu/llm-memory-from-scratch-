from __future__ import annotations

from typing import Protocol

from llm_memory.conversation.state import Message


class ConversationSummarizer(Protocol):
    def summarize(self, messages: list[Message]) -> Message:
        ...
