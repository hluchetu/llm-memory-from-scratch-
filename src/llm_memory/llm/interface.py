from __future__ import annotations

from typing import Protocol

from llm_memory.llm.message import AIMessage
from llm_memory.llm.message import Message


class ChatModel(Protocol):
    def invoke(self, messages: list[Message]) -> AIMessage:
        ...
