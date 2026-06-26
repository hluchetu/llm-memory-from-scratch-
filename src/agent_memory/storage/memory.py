from __future__ import annotations

from agent_memory.short_term.conversation.state import ConversationItem
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message


class MemoryStorage:
    def __init__(self) -> None:
        self._states: dict[str, ConversationState] = {}

    def get(self, thread_id: str) -> ConversationState | None:
        return self._states.get(thread_id)

    def save(self, state: ConversationState) -> None:
        self._states[state.thread_id] = state

    def create_thread(self, thread_id: str) -> None:
        self._states.setdefault(thread_id, ConversationState(thread_id=thread_id))

    def append_message(self, thread_id: str, message: Message) -> None:
        self.append_item(thread_id, message)

    def append_item(self, thread_id: str, item: ConversationItem) -> None:
        self.create_thread(thread_id)
        self._states[thread_id].items.append(item)

    def get_items_since(
        self,
        thread_id: str,
        item_id: str,
    ) -> list[ConversationItem]:
        state = self.get(thread_id)

        if state is None:
            return []

        return state.items_since(item_id)

    def replace_items(
        self,
        thread_id: str,
        items: list[ConversationItem],
    ) -> None:
        self._states[thread_id] = ConversationState(
            thread_id=thread_id,
            items=items,
        )

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self.replace_items(thread_id, messages)

    def delete(self, thread_id: str) -> None:
        self._states.pop(thread_id, None)
