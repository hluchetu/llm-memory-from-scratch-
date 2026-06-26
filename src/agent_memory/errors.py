class LLMMemoryError(Exception):
    """Base error for LLM memory failures."""


class InvalidProcessorConfigError(ValueError, LLMMemoryError):
    """Raised when a memory processor is configured incorrectly."""


class MessageSummarizationError(LLMMemoryError):
    """Raised when conversation summarization fails."""


class MemoryExtractionError(LLMMemoryError):
    """Raised when long-term memory extraction fails."""


class AgentRunError(LLMMemoryError):
    """Raised when an agent turn cannot complete."""


class AgentOutputValidationError(AgentRunError):
    """Raised when an agent response cannot be parsed into the expected output."""


class ContextBudgetExceededError(LLMMemoryError):
    """Raised when required context cannot fit within the token budget."""


class StorageError(LLMMemoryError):
    """Raised when conversation state cannot be persisted or loaded."""


class NamespaceAccessError(PermissionError, LLMMemoryError):
    """Raised when a namespace policy rejects a memory operation."""
