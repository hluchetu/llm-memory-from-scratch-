from __future__ import annotations

import pytest

from agent_memory.errors import InvalidProcessorConfigError
from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import Message as LLMMessage
from agent_memory.short_term.conversation.processors import ProcessingContext
from agent_memory.short_term.conversation.processors import SummarizeOldMessagesProcessor
from agent_memory.short_term.conversation.state import Message


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
