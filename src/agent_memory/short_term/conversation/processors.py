from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import MessageRole
from agent_memory.errors import ContextBudgetExceededError
from agent_memory.errors import InvalidProcessorConfigError
from agent_memory.errors import MessageSummarizationError
from agent_memory.llm.interface import ChatModel
from agent_memory.llm.message import HumanMessage
from agent_memory.llm.message import SystemMessage
from agent_memory.prompts.loader import load_prompt


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


class TokenCounter(Protocol):
    def count_message(self, message: Message) -> int:
        ...


class KeepWithinTokenBudgetProcessor:
    def __init__(
        self,
        max_tokens: int,
        token_counter: TokenCounter,
        preserve_system_messages: bool = True,
    ) -> None:
        if max_tokens <= 0:
            raise InvalidProcessorConfigError(
                "max_tokens must be greater than 0."
            )

        self._max_tokens = max_tokens
        self._token_counter = token_counter
        self._preserve_system_messages = preserve_system_messages

    def process(
        self,
        messages: list[Message],
        context: ProcessingContext,
    ) -> list[Message]:
        if not messages:
            return messages

        preserved_messages, candidate_messages = self._split_preserved_messages(
            messages
        )
        used_tokens = self._count_messages(preserved_messages)

        if used_tokens > self._max_tokens:
            raise ContextBudgetExceededError(
                "Preserved system messages exceed the token budget."
            )

        selected_units: list[list[Message]] = []
        message_units = self._group_message_units(candidate_messages)

        for unit in reversed(message_units):
            unit_tokens = self._count_messages(unit)

            if used_tokens + unit_tokens > self._max_tokens:
                if not selected_units:
                    raise ContextBudgetExceededError(
                        "The newest message group exceeds the remaining token budget."
                    )

                break

            selected_units.append(unit)
            used_tokens += unit_tokens

        selected_messages = [
            message
            for unit in reversed(selected_units)
            for message in unit
        ]

        return [
            *preserved_messages,
            *selected_messages,
        ]

    def _split_preserved_messages(
        self,
        messages: list[Message],
    ) -> tuple[list[Message], list[Message]]:
        if not self._preserve_system_messages:
            return [], messages

        preserved_messages: list[Message] = []
        candidate_index = 0

        for message in messages:
            if message.role != "system":
                break

            preserved_messages.append(message)
            candidate_index += 1

        return preserved_messages, messages[candidate_index:]

    def _group_message_units(
        self,
        messages: list[Message],
    ) -> list[list[Message]]:
        units: list[list[Message]] = []
        index = 0

        while index < len(messages):
            message = messages[index]
            unit = [message]
            index += 1

            if message.role == "assistant" and message.tool_calls:
                while index < len(messages) and messages[index].role == "tool":
                    unit.append(messages[index])
                    index += 1

            units.append(unit)

        return units

    def _count_messages(self, messages: list[Message]) -> int:
        return sum(
            self._token_counter.count_message(message)
            for message in messages
        )


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


class CompactToolInteractionsProcessor:
    def __init__(
        self,
        keep_recent_tool_interactions: int,
        max_tool_result_chars: int = 500,
    ) -> None:
        if keep_recent_tool_interactions < 0:
            raise InvalidProcessorConfigError(
                "keep_recent_tool_interactions must be greater than or equal to 0."
            )

        if max_tool_result_chars <= 0:
            raise InvalidProcessorConfigError(
                "max_tool_result_chars must be greater than 0."
            )

        self._keep_recent_tool_interactions = keep_recent_tool_interactions
        self._max_tool_result_chars = max_tool_result_chars

    def process(
        self,
        messages: list[Message],
        context: ProcessingContext,
    ) -> list[Message]:
        units = self._group_message_units(messages)
        tool_unit_indexes = [
            index
            for index, unit in enumerate(units)
            if self._is_tool_interaction(unit)
        ]
        compact_count = max(
            0,
            len(tool_unit_indexes) - self._keep_recent_tool_interactions,
        )
        compact_unit_indexes = set(tool_unit_indexes[:compact_count])
        processed_messages: list[Message] = []

        for index, unit in enumerate(units):
            if index in compact_unit_indexes:
                processed_messages.append(self._compact_unit(unit))
                continue

            processed_messages.extend(unit)

        return processed_messages

    def _group_message_units(
        self,
        messages: list[Message],
    ) -> list[list[Message]]:
        units: list[list[Message]] = []
        index = 0

        while index < len(messages):
            message = messages[index]
            unit = [message]
            index += 1

            if self._starts_tool_interaction(message):
                while index < len(messages) and messages[index].role == "tool":
                    unit.append(messages[index])
                    index += 1

            units.append(unit)

        return units

    def _is_tool_interaction(self, unit: list[Message]) -> bool:
        return bool(unit) and self._starts_tool_interaction(unit[0])

    def _starts_tool_interaction(self, message: Message) -> bool:
        return message.role == "assistant" and bool(message.tool_calls)

    def _compact_unit(self, unit: list[Message]) -> Message:
        assistant_message = unit[0]
        tool_messages = unit[1:]
        covered_item_ids = [
            message.id
            for message in unit
        ]
        lines = [
            "Compacted older tool interaction.",
            "The raw tool call and tool result messages were omitted from model context.",
            "",
            "Tool calls:",
        ]

        for tool_call in assistant_message.tool_calls:
            lines.append(f"- {tool_call.name}: {tool_call.arguments}")

        if assistant_message.content.strip():
            lines.extend(
                [
                    "",
                    f"Assistant note: {assistant_message.content.strip()}",
                ]
            )

        if tool_messages:
            lines.extend(
                [
                    "",
                    "Tool results:",
                ]
            )

            for message in tool_messages:
                tool_name = str(message.metadata.get("name", "tool"))
                lines.append(
                    f"- {tool_name}: {self._truncate(message.content)}"
                )

        return Message(
            role="system",
            content="\n".join(lines),
            metadata={
                "kind": "tool_interaction_compaction",
                "covered_item_ids": covered_item_ids,
            },
        )

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_tool_result_chars:
            return text

        return f"{text[: self._max_tool_result_chars].rstrip()}..."


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
