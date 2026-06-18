from __future__ import annotations

from llm_memory.context.conversation.state import ConversationItem
from llm_memory.context.conversation.state import ConversationState
from llm_memory.context.conversation.state import Message
from llm_memory.context.conversation.state import MessageRole
from llm_memory.context.conversation.state import SummaryItem
from llm_memory.storage.interface import ConversationStorage
from llm_memory.storage.memory import MemoryStorage


class ConversationMemory:
    def __init__(self, storage: ConversationStorage | None = None) -> None:
        self._storage = storage or MemoryStorage()

    def get_thread(self, thread_id: str) -> ConversationState:
        state = self._storage.get(thread_id)

        if state is None:
            self._storage.create_thread(thread_id)
            state = ConversationState(thread_id=thread_id)

        return state

    def add_message(
        self,
        thread_id: str,
        role: MessageRole,
        content: str,
        run_id: str | None = None,
        model_name: str | None = None,
        usage: dict[str, int] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Message:
        message = Message(
            role=role,
            content=content,
            run_id=run_id,
            model_name=model_name,
            usage=usage,
            metadata=metadata or {},
        )

        self._storage.append_message(
            thread_id=thread_id,
            message=message,
        )

        return message

    def add_summary(
        self,
        thread_id: str,
        content: str,
        covered_item_ids: list[str],
        metadata: dict[str, object] | None = None,
    ) -> SummaryItem:
        summary = SummaryItem(
            content=content,
            covered_item_ids=covered_item_ids,
            metadata=metadata or {},
        )

        self._storage.append_item(
            thread_id=thread_id,
            item=summary,
        )

        return summary

    def get_items(self, thread_id: str) -> list[ConversationItem]:
        state = self.get_thread(thread_id)

        return list(state.items)

    def get_messages(self, thread_id: str) -> list[Message]:
        state = self.get_thread(thread_id)

        return list(state.messages)

    def replace_messages(
        self,
        thread_id: str,
        messages: list[Message],
    ) -> None:
        self._storage.replace_messages(
            thread_id=thread_id,
            messages=messages,
        )

    def clear_thread(self, thread_id: str) -> None:
        self._storage.delete(thread_id)
