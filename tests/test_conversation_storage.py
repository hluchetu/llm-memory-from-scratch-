from __future__ import annotations

from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import SummaryItem
from agent_memory.short_term.conversation.memory import ConversationMemory
from agent_memory.storage.json import JsonStorage
from agent_memory.storage.markdown import MarkdownStorage
from agent_memory.storage.memory import MemoryStorage
from agent_memory.storage.sqlite import SQLiteStorage


def test_json_storage_preserves_pinned_items(tmp_path) -> None:
    storage = JsonStorage(tmp_path / "conversations.json")
    storage.save(build_pinned_state())

    state = storage.get("thread")

    assert state is not None
    assert [item.pinned for item in state.items] == [True, True]


def test_markdown_storage_preserves_pinned_items(tmp_path) -> None:
    storage = MarkdownStorage(tmp_path)
    storage.save(build_pinned_state())

    state = storage.get("thread")

    assert state is not None
    assert [item.pinned for item in state.items] == [True, True]


def test_sqlite_storage_preserves_pinned_items(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "conversations.sqlite")
    storage.save(build_pinned_state())

    state = storage.get("thread")

    assert state is not None
    assert [item.pinned for item in state.items] == [True, True]


def test_memory_storage_get_items_since() -> None:
    storage = MemoryStorage()
    state = build_three_message_state()
    storage.save(state)

    assert item_ids(storage.get_items_since("thread", "first")) == ["second", "third"]


def test_json_storage_get_items_since(tmp_path) -> None:
    storage = JsonStorage(tmp_path / "conversations.json")
    state = build_three_message_state()
    storage.save(state)

    assert item_ids(storage.get_items_since("thread", "first")) == ["second", "third"]


def test_markdown_storage_get_items_since(tmp_path) -> None:
    storage = MarkdownStorage(tmp_path)
    state = build_three_message_state()
    storage.save(state)

    assert item_ids(storage.get_items_since("thread", "first")) == ["second", "third"]


def test_sqlite_storage_get_items_since(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "conversations.sqlite")
    state = build_three_message_state()
    storage.save(state)

    assert item_ids(storage.get_items_since("thread", "first")) == ["second", "third"]


def test_storage_get_items_since_returns_all_items_when_anchor_is_missing(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "conversations.sqlite")
    state = build_three_message_state()
    storage.save(state)

    assert item_ids(storage.get_items_since("thread", "missing")) == [
        "first",
        "second",
        "third",
    ]


def test_conversation_memory_exposes_get_items_since() -> None:
    storage = MemoryStorage()
    memory = ConversationMemory(storage=storage)
    state = build_three_message_state()
    storage.save(state)

    assert item_ids(memory.get_items_since("thread", "first")) == ["second", "third"]


def build_pinned_state() -> ConversationState:
    return ConversationState(
        thread_id="thread",
        items=[
            Message(
                id="message",
                role="system",
                content="Pinned message.",
                pinned=True,
            ),
            SummaryItem(
                id="summary",
                content="Pinned summary.",
                covered_item_ids=["message"],
                pinned=True,
            ),
        ],
    )


def build_three_message_state() -> ConversationState:
    return ConversationState(
        thread_id="thread",
        items=[
            Message(id="first", role="user", content="First."),
            Message(id="second", role="assistant", content="Second."),
            Message(id="third", role="user", content="Third."),
        ],
    )


def item_ids(items) -> list[str]:
    return [item.id for item in items]
