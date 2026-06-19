from __future__ import annotations

from typing import Any
from typing import Literal
from typing import Union

from pydantic import BaseModel
from pydantic import Field


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class SystemMessage(BaseModel):
    type: Literal["system"] = "system"
    content: str


class HumanMessage(BaseModel):
    type: Literal["human"] = "human"
    content: str


class AIMessage(BaseModel):
    type: Literal["ai"] = "ai"
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: dict[str, int] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolMessage(BaseModel):
    type: Literal["tool"] = "tool"
    tool_call_id: str
    content: str
    status: Literal["success", "error"] = "success"
    metadata: dict[str, Any] = Field(default_factory=dict)


Message = Union[
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
]
