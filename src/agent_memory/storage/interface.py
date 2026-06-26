from __future__ import annotations

from typing import Protocol

from agent_memory.short_term.conversation.state import ConversationItem
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message


class ConversationStorage(Protocol):
    def get(self, thread_id: str) -> ConversationState | None:
        ...

    def create_thread(self, thread_id: str) -> None:
        ...

    def append_message(self, thread_id: str, message: Message) -> None:
        ...

    def append_item(self, thread_id: str, item: ConversationItem) -> None:
        ...

    def get_items_since(
        self,
        thread_id: str,
        item_id: str,
    ) -> list[ConversationItem]:
        ...

    def replace_items(
        self,
        thread_id: str,
        items: list[ConversationItem],
    ) -> None:
        ...

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        ...

    def delete(self, thread_id: str) -> None:
        ...
