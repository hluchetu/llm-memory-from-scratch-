from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class AgentSession:
    thread_id: str
    namespace: tuple[str, ...] | None = None
