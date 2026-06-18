from __future__ import annotations

from llm_memory.conversation.state import ConversationState
from llm_memory.conversation.state import Message


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
        self.create_thread(thread_id)
        self._states[thread_id].messages.append(message)

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self._states[thread_id] = ConversationState(
            thread_id=thread_id,
            messages=messages,
        )

    def delete(self, thread_id: str) -> None:
        self._states.pop(thread_id, None)
