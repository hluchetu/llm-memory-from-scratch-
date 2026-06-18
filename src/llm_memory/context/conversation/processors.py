from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llm_memory.context.conversation.state import Message
from llm_memory.context.conversation.state import MessageRole
from llm_memory.errors import InvalidProcessorConfigError
from llm_memory.errors import MessageSummarizationError
from llm_memory.llm.interface import ChatModel
from llm_memory.llm.message import HumanMessage
from llm_memory.llm.message import SystemMessage
from llm_memory.prompts.loader import load_prompt


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


class SummarizeOldMessagesProcessor:
    def __init__(
        self,
        model: ChatModel,
        trigger_message_count: int,
        keep_recent_messages: int,
    ) -> None:
        if trigger_message_count <= 0:
            raise InvalidProcessorConfigError(
                "trigger_message_count must be greater than 0."
            )

        if keep_recent_messages <= 0:
            raise InvalidProcessorConfigError(
                "keep_recent_messages must be greater than 0."
            )

        if keep_recent_messages >= trigger_message_count:
            raise InvalidProcessorConfigError(
                "keep_recent_messages must be smaller than trigger_message_count."
            )

        self._model = model
        self._trigger_message_count = trigger_message_count
        self._keep_recent_messages = keep_recent_messages

    def process(
        self,
        messages: list[Message],
        context: ProcessingContext,
    ) -> list[Message]:
        if len(messages) < self._trigger_message_count:
            return messages

        old_messages = messages[: -self._keep_recent_messages]
        recent_messages = messages[-self._keep_recent_messages :]
        summary = self._summarize(old_messages)

        summary_message = Message(
            role="system",
            content=f"Conversation summary so far:\n{summary}",
            metadata={
                "kind": "conversation_summary",
                "covered_item_ids": [
                    message.id
                    for message in old_messages
                ],
            },
        )

        return [
            summary_message,
            *recent_messages,
        ]

    def _summarize(self, messages: list[Message]) -> str:
        prompt = load_prompt(
            file_name="conversation_summary.yaml",
            prompt_name="conversation_summary",
        )

        try:
            response = self._model.invoke(
                [
                    SystemMessage(
                        content=prompt["system"]
                    ),
                    HumanMessage(
                        content=prompt["user"].format(
                            conversation=self._format_messages(messages)
                        )
                    ),
                ]
            )
        except Exception as error:
            raise MessageSummarizationError(
                "Failed to summarize old conversation messages."
            ) from error

        return response.content.strip()

    def _format_messages(self, messages: list[Message]) -> str:
        lines: list[str] = []

        for message in messages:
            lines.append(f"{message.role}: {message.content}")

        return "\n".join(lines)


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
