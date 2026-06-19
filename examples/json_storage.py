from __future__ import annotations

from pathlib import Path

from agent_memory.context.conversation.memory import ConversationMemory
from agent_memory.storage.json import JsonStorage


def main() -> None:
    storage = JsonStorage(path=Path(".memory") / "conversations.json")
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
    )

    loaded_memory = ConversationMemory(storage=storage)
    messages = loaded_memory.get_messages("thread-rag")

    for message in messages:
        print(message.role, message.content)


if __name__ == "__main__":
    main()
