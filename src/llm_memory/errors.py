class LLMMemoryError(Exception):
    """Base error for LLM memory failures."""


class InvalidProcessorConfigError(ValueError, LLMMemoryError):
    """Raised when a memory processor is configured incorrectly."""


class MessageSummarizationError(LLMMemoryError):
    """Raised when conversation summarization fails."""


class StorageError(LLMMemoryError):
    """Raised when conversation state cannot be persisted or loaded."""

