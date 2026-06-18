from __future__ import annotations

from pathlib import Path

from llm_memory.context.conversation.memory import ConversationMemory
from llm_memory.storage.cached import CachedConversationStorage
from llm_memory.storage.memory import MemoryStorage
from llm_memory.storage.sqlite import SQLiteStorage


def main() -> None:
    storage = CachedConversationStorage(
        cache=MemoryStorage(),
        primary=SQLiteStorage(path=Path(".memory") / "cached_conversations.db"),
    )
    memory = ConversationMemory(storage=storage)
    memory.clear_thread("thread-rag")

    memory.add_message(
        thread_id="thread-rag",
        role="user",
        content="Explain cached storage.",
    )
    memory.add_message(
        thread_id="thread-rag",
        role="assistant",
        content="Cached storage reads from memory first and writes to primary storage.",
        run_id="run-001",
        model_name="gpt-5.2",
        usage={
            "input_tokens": 30,
            "output_tokens": 14,
        },
        metadata={
            "finish_reason": "stop",
        },
    )

    messages = memory.get_messages("thread-rag")

    for message in messages:
        print(message.role, message.content, message.run_id, message.model_name)


if __name__ == "__main__":
    main()
