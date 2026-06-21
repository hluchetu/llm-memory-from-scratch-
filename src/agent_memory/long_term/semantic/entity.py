from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType


@dataclass(frozen=True, kw_only=True)
class EntityMemory(LongTermRecord):
    memory_type: ClassVar[MemoryType] = "entity"
    name: str
    description: str
