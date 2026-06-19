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


class OpenAICompatibleChatModel(ChatModel):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float,
        max_output_tokens: int,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    def invoke(self, messages: list[Message]) -> AIMessage:
        payload = {
            "model": self._model,
            "messages": [
                self._to_provider_message(message)
                for message in messages
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_output_tokens,
        }
        response = self._post_json(
            url=f"{self._base_url}/chat/completions",
            payload=payload,
        )
        choice = response["choices"][0]
        message = choice["message"]

        return AIMessage(
            content=message.get("content") or "",
            usage=self._extract_usage(response),
            metadata={
                "id": response.get("id"),
                "model": response.get("model"),
                "finish_reason": choice.get("finish_reason"),
            },
        )

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
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
                f"Model provider request failed with status {error.code}: {body}"
            ) from error

    def _to_provider_message(self, message: Message) -> dict[str, str]:
        if isinstance(message, SystemMessage):
            return {
                "role": "system",
                "content": message.content,
            }

        if isinstance(message, HumanMessage):
            return {
                "role": "user",
                "content": message.content,
            }

        if isinstance(message, AIMessage):
            return {
                "role": "assistant",
                "content": message.content,
            }

        if isinstance(message, ToolMessage):
            return {
                "role": "tool",
                "content": message.content,
            }

        raise TypeError(f"Unsupported message type: {type(message).__name__}")

    def _extract_usage(self, response: dict[str, Any]) -> dict[str, int] | None:
        usage = response.get("usage")

        if not isinstance(usage, dict):
            return None

        return {
            key: value
            for key, value in usage.items()
            if isinstance(value, int)
        }
