from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from agent_memory.agent.tool import AgentTool
from agent_memory.llm.interface import ChatModel


@dataclass(frozen=True, kw_only=True)
class Agent:
    name: str
    instructions: str
    model: ChatModel
    tools: list[AgentTool] | None = None
    output_schema: type[BaseModel] | None = None
    model_settings: dict[str, Any] | None = None
