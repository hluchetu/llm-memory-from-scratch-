from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType


@dataclass(frozen=True, kw_only=True)
class EventMemory(LongTermRecord):
    memory_type: ClassVar[MemoryType] = "episodic"
    description: str
    occurred_at: datetime
