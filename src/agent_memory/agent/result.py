from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from agent_memory.context import MemoryContextResult
from agent_memory.long_term.item import LongTermRecord
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import ToolCall
from agent_memory.short_term.conversation.state import ToolResult


AgentOutput = str | BaseModel


@dataclass(frozen=True, kw_only=True)
class AgentResult:
    run_id: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    assistant_message: Message
    output: AgentOutput
    raw_output: str
    memory_context: MemoryContextResult | None = None
    extracted_records: list[LongTermRecord] | None = None
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    usage: dict[str, int] | None = None
    metadata: dict[str, Any] | None = None

    @property
    def context_record_ids(self) -> list[str]:
        if self.memory_context is None:
            return []

        return self.memory_context.record_ids
