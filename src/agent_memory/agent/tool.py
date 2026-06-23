from __future__ import annotations

from typing import Any
from typing import Protocol


class AgentTool(Protocol):
    name: str
    description: str

    def __call__(self, **kwargs: Any) -> Any:
        ...
