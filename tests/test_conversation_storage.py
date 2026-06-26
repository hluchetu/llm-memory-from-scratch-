from __future__ import annotations

from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import SummaryItem
from agent_memory.storage.json import JsonStorage
from agent_memory.storage.markdown import MarkdownStorage
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
