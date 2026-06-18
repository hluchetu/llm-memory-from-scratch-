from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llm_memory.conversation.state import Message
from llm_memory.conversation.state import MessageRole


@dataclass(frozen=True)
class ProcessingContext:
    current_input: str | None = None


class MessageHistoryProcessor(Protocol):
    def process(
        self,
        messages: list[Message],
        context: ProcessingContext,
    ) -> list[Message]:
        ...


class KeepRecentMessagesProcessor:
    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages

    def process(
        self,
        messages: list[Message],
        context: ProcessingContext,
    ) -> list[Message]:
        if len(messages) <= self._max_messages:
            return messages

        return messages[-self._max_messages :]


class FilterByRoleProcessor:
    def __init__(self, allowed_roles: set[MessageRole]) -> None:
        self._allowed_roles = allowed_roles

    def process(
        self,
        messages: list[Message],
        context: ProcessingContext,
    ) -> list[Message]:
        return [
            message
            for message in messages
            if message.role in self._allowed_roles
        ]


class ProcessorPipeline:
    def __init__(self, processors: list[MessageHistoryProcessor]) -> None:
        self._processors = processors

    def process(
        self,
        messages: list[Message],
        context: ProcessingContext | None = None,
    ) -> list[Message]:
        processed_messages = messages
        processing_context = context or ProcessingContext()

        for processor in self._processors:
            processed_messages = processor.process(
                messages=processed_messages,
                context=processing_context,
            )

        return processed_messages
