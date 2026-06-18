from __future__ import annotations

from typing import Protocol

from llm_memory.conversation.state import ConversationState
from llm_memory.conversation.state import Message


class ConversationStorage(Protocol):
    def get(self, thread_id: str) -> ConversationState | None:
        ...

    def create_thread(self, thread_id: str) -> None:
        ...

    def append_message(self, thread_id: str, message: Message) -> None:
        ...

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        ...

    def delete(self, thread_id: str) -> None:
        ...
