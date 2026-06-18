from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Literal
from uuid import uuid4


ConversationItemType = Literal[
    "message",
    "tool_call",
    "tool_result",
    "retrieval",
    "summary",
]

MessageRole = Literal["system", "user", "assistant", "tool"]


def new_item_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ConversationItem:
    id: str = field(default_factory=new_item_id)
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall(ConversationItem):
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    tool_call_id: str = field(default_factory=new_item_id)
    item_type: Literal["tool_call"] = "tool_call"


@dataclass(frozen=True)
class Message(ConversationItem):
    role: MessageRole = "user"
    content: str = ""
    run_id: str | None = None
    model_name: str | None = None
    usage: dict[str, int] | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    item_type: Literal["message"] = "message"


@dataclass(frozen=True)
class ToolResult(ConversationItem):
    tool_call_id: str = ""
    name: str = ""
    content: str = ""
    artifact: dict[str, Any] | None = None
    item_type: Literal["tool_result"] = "tool_result"


@dataclass(frozen=True)
class RetrievalItem(ConversationItem):
    query: str = ""
    content: str = ""
    source_ids: list[str] = field(default_factory=list)
    item_type: Literal["retrieval"] = "retrieval"


@dataclass(frozen=True)
class SummaryItem(ConversationItem):
    content: str = ""
    covered_item_ids: list[str] = field(default_factory=list)
    item_type: Literal["summary"] = "summary"


@dataclass
class ConversationState:
    thread_id: str
    items: list[ConversationItem] = field(default_factory=list)

    @property
    def messages(self) -> list[Message]:
        return [item for item in self.items if isinstance(item, Message)]

