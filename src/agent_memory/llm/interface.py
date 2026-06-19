from __future__ import annotations

from typing import Protocol

from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import Message


class ChatModel(Protocol):
    def invoke(self, messages: list[Message]) -> AIMessage:
        ...
