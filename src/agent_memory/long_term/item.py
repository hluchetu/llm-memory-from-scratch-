from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import ClassVar
from typing import Literal
from uuid import uuid4

from agent_memory.utils.time import utc_now


MemoryType = Literal[
    "semantic",
    "entity",
    "episodic",
    "procedural",
    "preference",
    "decision",
]


def new_memory_id() -> str:
    return str(uuid4())


@dataclass(frozen=True, kw_only=True)
class LongTermRecord:
    memory_type: ClassVar[MemoryType]
    namespace: tuple[str, ...]
    key: str
    id: str = field(default_factory=new_memory_id)
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    invalidated_at: datetime | None = None
    importance: float | None = None
    related_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self) is LongTermRecord:
            raise TypeError("LongTermRecord is a base class. Use a typed record.")
