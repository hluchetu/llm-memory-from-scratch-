from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 2.0
    max_delay: float = 30.0


def with_retry(
    fn: Callable[[], T],
    config: RetryConfig,
    is_transient: Callable[[Exception], bool],
) -> T:
    last_error: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            return fn()
        except Exception as error:
            if not is_transient(error):
                raise

            last_error = error

            if attempt < config.max_attempts - 1:
                delay = min(
                    config.initial_delay * (2 ** attempt),
                    config.max_delay,
                )
                time.sleep(delay)

    raise last_error  # type: ignore[misc]


def is_transient_llm_error(error: Exception) -> bool:
    error_type = type(error).__name__.lower()
    error_msg = str(error).lower()
    signals = ("rate", "timeout", "unavailable", "overloaded", "503", "529", "too many")
    return any(s in error_type or s in error_msg for s in signals)


def is_transient_storage_error(error: Exception) -> bool:
    error_type = type(error).__name__.lower()
    error_msg = str(error).lower()
    signals = ("locked", "timeout", "disk", "busy", "connection")
    return any(s in error_type or s in error_msg for s in signals)
