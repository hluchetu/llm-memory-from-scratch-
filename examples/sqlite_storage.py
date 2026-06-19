from __future__ import annotations

from pathlib import Path

from agent_memory.context.conversation.memory import ConversationMemory
from agent_memory.storage.sqlite import SQLiteStorage


def main() -> None:
    storage = SQLiteStorage(path=Path(".memory") / "conversations.db")
    memory = ConversationMemory(storage=storage)
    memory.clear_thread("thread-rag")

    memory.add_message(
        thread_id="thread-rag",
        role="user",
        content="Explain reranking.",
    )
    memory.add_message(
        thread_id="thread-rag",
        role="assistant",
        content="Reranking sorts retrieved documents by relevance.",
        run_id="run-001",
        model_name="gpt-5.2",
        usage={
            "input_tokens": 42,
            "output_tokens": 12,
        },
        metadata={
            "finish_reason": "stop",
        },
    )

    loaded_memory = ConversationMemory(storage=storage)
    messages = loaded_memory.get_messages("thread-rag")

    for message in messages:
        print(message.role, message.content, message.run_id, message.model_name)


if __name__ == "__main__":
    main()
