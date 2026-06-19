from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Literal
from uuid import uuid4


MemoryType = Literal[
    "semantic",
    "episodic",
    "procedural",
    "preference",
    "decision",
]


def new_memory_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class MemoryRecord:
    namespace: tuple[str, ...]
    key: str
    value: str
    memory_type: MemoryType
    id: str = field(default_factory=new_memory_id)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

