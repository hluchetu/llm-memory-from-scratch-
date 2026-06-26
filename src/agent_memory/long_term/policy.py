from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class NamespacePolicy(Protocol):
    def can_read(self, namespace: tuple[str, ...]) -> bool:
        ...

    def can_write(self, namespace: tuple[str, ...]) -> bool:
        ...


class AllowAllNamespacePolicy:
    def can_read(self, namespace: tuple[str, ...]) -> bool:
        return True

    def can_write(self, namespace: tuple[str, ...]) -> bool:
        return True


@dataclass(frozen=True)
class NamespacePrefixPolicy:
    allowed_prefix: tuple[str, ...]
    allow_reads: bool = True
    allow_writes: bool = True

    def can_read(self, namespace: tuple[str, ...]) -> bool:
        return self.allow_reads and self._matches(namespace)

    def can_write(self, namespace: tuple[str, ...]) -> bool:
        return self.allow_writes and self._matches(namespace)

    def _matches(self, namespace: tuple[str, ...]) -> bool:
        return namespace[: len(self.allowed_prefix)] == self.allowed_prefix
