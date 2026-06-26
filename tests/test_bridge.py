from __future__ import annotations

import pytest

from agent_memory.bridge import conversation_state_to_messages
from agent_memory.bridge import messages_to_conversation_state
from agent_memory.bridge import normalize_content
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import ToolResult


def test_messages_to_conversation_state_converts_plain_messages() -> None:
    state = messages_to_conversation_state(
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "I prefer concise answers."},
            {"role": "assistant", "content": "Got it."},
        ],
        thread_id="thread",
    )

    assert state.thread_id == "thread"
    assert [message.role for message in state.messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert [message.content for message in state.messages] == [
        "You are helpful.",
        "I prefer concise answers.",
        "Got it.",
    ]


def test_normalize_content_extracts_text_from_multimodal_parts() -> None:
    content = normalize_content(
        [
            {"type": "text", "text": "Describe this image."},
            {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
            {"text": "Only text parts become memory input."},
        ]
    )

    assert content == "Describe this image.\nOnly text parts become memory input."


def test_missing_role_defaults_to_user_unless_strict() -> None:
    state = messages_to_conversation_state(
        [{"content": "No role was provided."}],
        thread_id="thread",
    )

    assert state.messages[0].role == "user"

    with pytest.raises(ValueError, match="missing role"):
        messages_to_conversation_state(
            [{"content": "No role was provided."}],
            thread_id="thread",
            strict=True,
        )


def test_bridge_preserves_tool_calls_and_tool_results() -> None:
    state = messages_to_conversation_state(
        [
            {
                "role": "assistant",
                "content": "Checking that now.",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "lookup",
                            "arguments": {"query": "memory"},
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-1",
                "name": "lookup",
                "content": "Found memory docs.",
            },
        ],
        thread_id="thread",
    )

    assert isinstance(state.items[0], Message)
    assert state.items[0].tool_calls[0].name == "lookup"
    assert state.items[0].tool_calls[0].arguments == {"query": "memory"}
    assert isinstance(state.items[1], ToolResult)
    assert state.items[1].tool_call_id == "call-1"


def test_conversation_state_to_messages_round_trips_supported_items() -> None:
    state = messages_to_conversation_state(
        [
            {"role": "user", "content": "Search for docs."},
            {
                "role": "tool",
                "tool_call_id": "call-1",
                "name": "search",
                "content": "Docs found.",
            },
        ],
        thread_id="thread",
    )

    assert conversation_state_to_messages(state) == [
        {"role": "user", "content": "Search for docs."},
        {
            "role": "tool",
            "tool_call_id": "call-1",
            "name": "search",
            "content": "Docs found.",
        },
    ]
