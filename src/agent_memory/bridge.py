from __future__ import annotations

from typing import Any

from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import MessageRole
from agent_memory.short_term.conversation.state import ToolCall
from agent_memory.short_term.conversation.state import ToolResult


ProviderMessage = dict[str, Any]


def messages_to_conversation_state(
    messages: list[ProviderMessage],
    thread_id: str,
    strict: bool = False,
) -> ConversationState:
    items = []

    for message in messages:
        role = normalize_role(message.get("role"), strict=strict)
        content = normalize_content(message.get("content"))
        tool_calls = normalize_tool_calls(message.get("tool_calls"))

        if role == "tool":
            items.append(
                ToolResult(
                    tool_call_id=str(message.get("tool_call_id") or ""),
                    name=str(message.get("name") or ""),
                    content=content,
                    metadata={"provider_message": message},
                )
            )
            continue

        items.append(
            Message(
                role=role,
                content=content,
                tool_calls=tool_calls,
                metadata={"provider_message": message},
            )
        )

    return ConversationState(thread_id=thread_id, items=items)


def conversation_state_to_messages(
    state: ConversationState,
) -> list[ProviderMessage]:
    messages: list[ProviderMessage] = []

    for item in state.items:
        if isinstance(item, Message):
            message: ProviderMessage = {
                "role": item.role,
                "content": item.content,
            }

            if item.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": tool_call.tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        },
                    }
                    for tool_call in item.tool_calls
                ]

            messages.append(message)

        if isinstance(item, ToolResult):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.tool_call_id,
                    "name": item.name,
                    "content": item.content,
                }
            )

    return messages


def normalize_content(content: Any) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                text = text_from_content_part(part)

                if text:
                    text_parts.append(text)

        return "\n".join(text_parts)

    return str(content)


def text_from_content_part(part: dict[str, Any]) -> str:
    if part.get("type") == "text":
        return str(part.get("text") or "")

    if "text" in part:
        return str(part.get("text") or "")

    return ""


def normalize_role(
    role: Any,
    strict: bool = False,
) -> MessageRole:
    if role is None:
        if strict:
            raise ValueError("Message is missing role.")
        return "user"

    normalized_role = str(role).strip().lower()

    if normalized_role in {"system", "user", "assistant", "tool"}:
        return normalized_role  # type: ignore[return-value]

    if strict:
        raise ValueError(f"Unsupported message role: {role}")

    return "user"


def normalize_tool_calls(value: Any) -> list[ToolCall]:
    if not isinstance(value, list):
        return []

    tool_calls = []

    for raw_tool_call in value:
        if not isinstance(raw_tool_call, dict):
            continue

        function = raw_tool_call.get("function") or {}

        if not isinstance(function, dict):
            function = {}

        tool_calls.append(
            ToolCall(
                tool_call_id=str(raw_tool_call.get("id") or ""),
                name=str(function.get("name") or raw_tool_call.get("name") or ""),
                arguments=normalize_tool_arguments(
                    function.get("arguments", raw_tool_call.get("arguments", {}))
                ),
                metadata={"provider_tool_call": raw_tool_call},
            )
        )

    return tool_calls


def normalize_tool_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {"value": value}
