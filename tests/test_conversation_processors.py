from __future__ import annotations

import pytest

from agent_memory.errors import InvalidProcessorConfigError
from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import Message as LLMMessage
from agent_memory.short_term.conversation.processors import ProcessingContext
from agent_memory.short_term.conversation.processors import CompactToolInteractionsProcessor
from agent_memory.short_term.conversation.processors import FilterByRoleProcessor
from agent_memory.short_term.conversation.processors import KeepWithinTokenBudgetProcessor
from agent_memory.short_term.conversation.processors import SummarizeOldMessagesProcessor
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import ToolCall


class WordTokenCounter:
    def count_message(self, message: Message) -> int:
        return len(message.content.split())


class FixedSummaryModel:
    def __init__(self) -> None:
        self.calls: list[list[LLMMessage]] = []

    def invoke(self, messages: list[LLMMessage]) -> AIMessage:
        self.calls.append(messages)
        return AIMessage(content="The user and assistant discussed project details.")


def make_messages(contents: list[str]) -> list[Message]:
    return [
        Message(role="user" if index % 2 == 0 else "assistant", content=content)
        for index, content in enumerate(contents)
    ]


def test_summarizer_does_not_trigger_when_tokens_are_under_limit() -> None:
    model = FixedSummaryModel()
    processor = SummarizeOldMessagesProcessor(
        model=model,
        keep_recent_messages=1,
        trigger_token_count=10,
        token_counter=WordTokenCounter(),
    )
    messages = make_messages(["short one", "short two", "short three"])

    processed = processor.process(messages, ProcessingContext())

    assert processed == messages
    assert model.calls == []


def test_summarizer_triggers_when_tokens_exceed_limit() -> None:
    model = FixedSummaryModel()
    processor = SummarizeOldMessagesProcessor(
        model=model,
        keep_recent_messages=1,
        trigger_token_count=5,
        token_counter=WordTokenCounter(),
    )
    messages = make_messages(
        [
            "one two three",
            "four five six",
            "recent message",
        ]
    )

    processed = processor.process(messages, ProcessingContext())

    assert len(processed) == 2
    assert processed[0].role == "system"
    assert processed[0].content == "\n".join(
        [
            "Conversation summary so far:",
            "The user and assistant discussed project details.",
        ]
    )
    assert processed[0].metadata["kind"] == "conversation_summary"
    assert processed[0].metadata["covered_item_ids"] == [
        messages[0].id,
        messages[1].id,
    ]
    assert processed[1] == messages[-1]
    assert len(model.calls) == 1


def test_summarizer_requires_token_counter_for_token_trigger() -> None:
    with pytest.raises(InvalidProcessorConfigError, match="token_counter"):
        SummarizeOldMessagesProcessor(
            model=FixedSummaryModel(),
            keep_recent_messages=1,
            trigger_token_count=10,
        )


def test_summarizer_still_supports_named_message_count_trigger() -> None:
    model = FixedSummaryModel()
    processor = SummarizeOldMessagesProcessor(
        model=model,
        keep_recent_messages=1,
        trigger_message_count=3,
    )
    messages = make_messages(["first", "second", "third"])

    processed = processor.process(messages, ProcessingContext())

    assert processed[0].role == "system"
    assert processed[1] == messages[-1]


def test_token_budget_processor_preserves_pinned_messages() -> None:
    pinned = Message(
        id="pinned",
        role="user",
        content="important instruction",
        pinned=True,
    )
    old = Message(id="old", role="user", content="old message")
    recent = Message(id="recent", role="assistant", content="recent answer")
    processor = KeepWithinTokenBudgetProcessor(
        max_tokens=4,
        token_counter=WordTokenCounter(),
        preserve_system_messages=False,
    )

    assert processor.process(
        [pinned, old, recent],
        ProcessingContext(),
    ) == [pinned, recent]


def test_filter_by_role_processor_preserves_pinned_messages() -> None:
    pinned_system = Message(
        role="system",
        content="Pinned policy.",
        pinned=True,
    )
    user = Message(role="user", content="Hello.")
    processor = FilterByRoleProcessor(allowed_roles={"user"})

    assert processor.process(
        [pinned_system, user],
        ProcessingContext(),
    ) == [pinned_system, user]


def test_tool_compaction_processor_preserves_pinned_tool_interaction() -> None:
    pinned_assistant = Message(
        role="assistant",
        content="Calling tool.",
        pinned=True,
        tool_calls=[
            ToolCall(
                name="search",
                arguments={"query": "memory"},
                tool_call_id="call-1",
            )
        ],
    )
    pinned_tool_result = Message(
        role="tool",
        content="Pinned result.",
    )
    compacted_assistant = Message(
        role="assistant",
        content="Calling older tool.",
        tool_calls=[
            ToolCall(
                name="lookup",
                arguments={"query": "old"},
                tool_call_id="call-2",
            )
        ],
    )
    compacted_tool_result = Message(role="tool", content="Older result.")
    processor = CompactToolInteractionsProcessor(keep_recent_tool_interactions=0)

    processed = processor.process(
        [
            pinned_assistant,
            pinned_tool_result,
            compacted_assistant,
            compacted_tool_result,
        ],
        ProcessingContext(),
    )

    assert processed[:2] == [pinned_assistant, pinned_tool_result]
    assert len(processed) == 3
    assert processed[2].metadata["kind"] == "tool_interaction_compaction"


def test_summarizer_preserves_pinned_old_messages_outside_summary() -> None:
    model = FixedSummaryModel()
    processor = SummarizeOldMessagesProcessor(
        model=model,
        keep_recent_messages=1,
        trigger_token_count=3,
        token_counter=WordTokenCounter(),
    )
    pinned = Message(id="pinned", role="system", content="Pinned.", pinned=True)
    old = Message(id="old", role="user", content="old message content")
    recent = Message(id="recent", role="assistant", content="recent answer")

    processed = processor.process([pinned, old, recent], ProcessingContext())

    assert processed[0] == pinned
    assert processed[1].metadata["covered_item_ids"] == ["old"]
    assert processed[2] == recent


def test_summarizer_carries_existing_summary_without_resummarizing_it() -> None:
    model = FixedSummaryModel()
    processor = SummarizeOldMessagesProcessor(
        model=model,
        keep_recent_messages=1,
        trigger_token_count=6,
        token_counter=WordTokenCounter(),
    )
    previous_summary = Message(
        id="summary",
        role="system",
        content="Conversation summary so far:\nEarlier summary.",
        metadata={
            "kind": "conversation_summary",
            "covered_item_ids": ["first"],
        },
    )
    new_old_message = Message(
        id="second",
        role="user",
        content="new old message",
    )
    recent = Message(id="recent", role="assistant", content="recent answer")

    processed = processor.process(
        [previous_summary, new_old_message, recent],
        ProcessingContext(),
    )

    assert len(processed) == 2
    assert processed[0].content == "\n".join(
        [
            "Conversation summary so far:",
            "Earlier summary.",
            "The user and assistant discussed project details.",
        ]
    )
    assert processed[0].metadata["covered_item_ids"] == ["first", "second"]
    assert processed[1] == recent
    assert len(model.calls) == 1
    assert "Earlier summary." not in model.calls[0][1].content
    assert "new old message" in model.calls[0][1].content


def test_summarizer_keeps_existing_summary_when_there_are_no_new_old_messages() -> None:
    model = FixedSummaryModel()
    processor = SummarizeOldMessagesProcessor(
        model=model,
        keep_recent_messages=1,
        trigger_token_count=4,
        token_counter=WordTokenCounter(),
    )
    previous_summary = Message(
        id="summary",
        role="system",
        content="Conversation summary so far:\nEarlier summary.",
        metadata={
            "kind": "conversation_summary",
            "covered_item_ids": ["first"],
        },
    )
    recent = Message(id="recent", role="assistant", content="recent answer")

    processed = processor.process(
        [previous_summary, recent],
        ProcessingContext(),
    )

    assert processed == [previous_summary, recent]
    assert model.calls == []
