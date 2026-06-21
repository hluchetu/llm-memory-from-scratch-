from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import MemoryType


@dataclass(frozen=True, kw_only=True)
class WorkflowMemory(LongTermRecord):
    memory_type: ClassVar[MemoryType] = "procedural"
    steps: list[str]
