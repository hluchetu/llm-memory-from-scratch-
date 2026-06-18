from __future__ import annotations

from llm_memory.context.conversation.state import Message as ConversationMessage
from llm_memory.context.conversation.state import ToolCall as ConversationToolCall
from llm_memory.llm.message import AIMessage
from llm_memory.llm.message import HumanMessage
from llm_memory.llm.message import Message
from llm_memory.llm.message import SystemMessage
from llm_memory.llm.message import ToolCall
from llm_memory.llm.message import ToolMessage


def to_llm_tool_call(tool_call: ConversationToolCall) -> ToolCall:
    return ToolCall(
        id=tool_call.tool_call_id,
        name=tool_call.name,
        args=tool_call.arguments,
    )


def to_llm_message(message: ConversationMessage) -> Message:
    if message.role == "system":
        return SystemMessage(content=message.content)

    if message.role == "user":
        return HumanMessage(content=message.content)

    if message.role == "assistant":
        return AIMessage(
            content=message.content,
            tool_calls=[
                to_llm_tool_call(tool_call)
                for tool_call in message.tool_calls
            ],
            usage=message.usage,
            metadata=message.metadata,
        )

    return ToolMessage(
        tool_call_id=str(message.metadata.get("tool_call_id", "")),
        content=message.content,
        metadata=message.metadata,
    )


def to_llm_messages(messages: list[ConversationMessage]) -> list[Message]:
    return [
        to_llm_message(message)
        for message in messages
    ]
