from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Literal
from uuid import uuid4


MessageRole = Literal["system", "user", "assistant", "tool"]


def new_message_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str
    id: str = field(default_factory=new_message_id)
    created_at: datetime = field(default_factory=utc_now)
    run_id: str | None = None
    model_name: str | None = None
    usage: dict[str, int] | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ConversationState:
    thread_id: str
    messages: list[Message] = field(default_factory=list)
