from __future__ import annotations

from agent_memory.extraction.llm import select_items
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message


def test_items_since_returns_items_after_matching_id() -> None:
    first = Message(id="first", content="First")
    second = Message(id="second", content="Second")
    third = Message(id="third", content="Third")
    state = ConversationState(thread_id="thread", items=[first, second, third])

    assert state.items_since("first") == [second, third]


def test_items_since_returns_all_items_when_id_is_unknown() -> None:
    first = Message(id="first", content="First")
    second = Message(id="second", content="Second")
    state = ConversationState(thread_id="thread", items=[first, second])

    assert state.items_since("missing") == [first, second]


def test_select_items_uses_conversation_state_items_since() -> None:
    first = Message(id="first", content="First")
    second = Message(id="second", content="Second")
    third = Message(id="third", content="Third")
    state = ConversationState(thread_id="thread", items=[first, second, third])

    assert select_items(
        conversation=state,
        since_item_id="first",
        max_items=1,
    ) == [third]
