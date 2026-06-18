from __future__ import annotations

from llm_memory.conversation.state import ConversationState
from llm_memory.conversation.state import Message
from llm_memory.storage.interface import ConversationStorage


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

        self._cache.replace_messages(
            thread_id=thread_id,
            messages=primary_state.messages,
        )

        return primary_state

    def create_thread(self, thread_id: str) -> None:
        self._primary.create_thread(thread_id)
        self._cache.create_thread(thread_id)

    def append_message(self, thread_id: str, message: Message) -> None:
        self._primary.append_message(thread_id, message)
        self._cache.append_message(thread_id, message)

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self._primary.replace_messages(thread_id, messages)
        self._cache.replace_messages(thread_id, messages)

    def delete(self, thread_id: str) -> None:
        self._primary.delete(thread_id)
        self._cache.delete(thread_id)
