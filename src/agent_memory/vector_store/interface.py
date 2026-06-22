from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol


@dataclass(frozen=True, kw_only=True)
class VectorSearchResult:
    record_id: str
    score: float


class VectorStore(Protocol):
    def upsert(
        self,
        record_id: str,
        vector: list[float],
        document: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...

    def search(
        self,
        vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        ...

    def delete(self, record_id: str) -> None:
        ...
