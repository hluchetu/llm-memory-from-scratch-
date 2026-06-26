from __future__ import annotations

from agent_memory.short_term.conversation.state import ConversationItem
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.storage.interface import ConversationStorage


class CachedConversationStorage:
    def __init__(
        self,
        cache: ConversationStorage,
        primary: ConversationStorage,
    ) -> None:
        self._cache = cache
        self._primary = primary

    def get(self, thread_id: str) -> ConversationState | None:
        cached_state = self._cache.get(thread_id)

        if cached_state is not None:
            return cached_state

        primary_state = self._primary.get(thread_id)

        if primary_state is None:
            return None

        self._cache.replace_items(
            thread_id=thread_id,
            items=primary_state.items,
        )

        return primary_state

    def create_thread(self, thread_id: str) -> None:
        self._primary.create_thread(thread_id)
        self._cache.create_thread(thread_id)

    def append_message(self, thread_id: str, message: Message) -> None:
        self.append_item(thread_id, message)

    def append_item(self, thread_id: str, item: ConversationItem) -> None:
        self._primary.append_item(thread_id, item)
        self._cache.append_item(thread_id, item)

    def get_items_since(
        self,
        thread_id: str,
        item_id: str,
    ) -> list[ConversationItem]:
        cached_state = self._cache.get(thread_id)

        if cached_state is not None:
            return cached_state.items_since(item_id)

        items = self._primary.get_items_since(thread_id, item_id)
        primary_state = self._primary.get(thread_id)

        if primary_state is not None:
            self._cache.replace_items(
                thread_id=thread_id,
                items=primary_state.items,
            )

        return items

    def replace_items(
        self,
        thread_id: str,
        items: list[ConversationItem],
    ) -> None:
        self._primary.replace_items(thread_id, items)
        self._cache.replace_items(thread_id, items)

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self.replace_items(thread_id, messages)

    def delete(self, thread_id: str) -> None:
        self._primary.delete(thread_id)
        self._cache.delete(thread_id)
