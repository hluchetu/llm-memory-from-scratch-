from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen

from agent_memory.llm.interface import ChatModel
from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import HumanMessage
from agent_memory.llm.message import Message
from agent_memory.llm.message import SystemMessage
from agent_memory.llm.message import ToolMessage


class AnthropicChatModel(ChatModel):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        anthropic_version: str,
        max_output_tokens: int,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._anthropic_version = anthropic_version
        self._max_output_tokens = max_output_tokens

    def invoke(self, messages: list[Message]) -> AIMessage:
        system_prompt, provider_messages = self._to_provider_messages(messages)
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_output_tokens,
            "messages": provider_messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = self._post_json(
            url=f"{self._base_url}/v1/messages",
            payload=payload,
        )

        return AIMessage(
            content=self._extract_text(response),
            usage=self._extract_usage(response),
            metadata={
                "id": response.get("id"),
                "model": response.get("model"),
                "stop_reason": response.get("stop_reason"),
            },
        )

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": self._anthropic_version,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8")
            raise RuntimeError(
                f"Anthropic request failed with status {error.code}: {body}"
            ) from error

    def _to_provider_messages(
        self,
        messages: list[Message],
    ) -> tuple[str | None, list[dict[str, str]]]:
        system_parts: list[str] = []
        provider_messages: list[dict[str, str]] = []

        for message in messages:
            if isinstance(message, SystemMessage):
                system_parts.append(message.content)
                continue

            if isinstance(message, HumanMessage):
                provider_messages.append(
                    {
                        "role": "user",
                        "content": message.content,
                    }
                )
                continue

            if isinstance(message, AIMessage):
                provider_messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                    }
                )
                continue

            if isinstance(message, ToolMessage):
                provider_messages.append(
                    {
                        "role": "user",
                        "content": f"Tool result: {message.content}",
                    }
                )
                continue

            raise TypeError(f"Unsupported message type: {type(message).__name__}")

        system_prompt = "\n\n".join(system_parts) or None

        return system_prompt, provider_messages

    def _extract_text(self, response: dict[str, Any]) -> str:
        content = response.get("content", [])
        text_parts: list[str] = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))

        return "\n".join(text_parts).strip()

    def _extract_usage(self, response: dict[str, Any]) -> dict[str, int] | None:
        usage = response.get("usage")

        if not isinstance(usage, dict):
            return None

        return {
            key: value
            for key, value in usage.items()
            if isinstance(value, int)
        }
