class LLMMemoryError(Exception):
    """Base error for LLM memory failures."""


class InvalidProcessorConfigError(ValueError, LLMMemoryError):
    """Raised when a memory processor is configured incorrectly."""


class MessageSummarizationError(LLMMemoryError):
    """Raised when conversation summarization fails."""


class MemoryExtractionError(LLMMemoryError):
    """Raised when long-term memory extraction fails."""


class ContextBudgetExceededError(LLMMemoryError):
    """Raised when required context cannot fit within the token budget."""


class StorageError(LLMMemoryError):
    """Raised when conversation state cannot be persisted or loaded."""
