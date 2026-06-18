from __future__ import annotations

from llm_memory.conversation.conversation import ConversationMemory
from llm_memory.conversation.processors import FilterByRoleProcessor
from llm_memory.conversation.processors import KeepRecentMessagesProcessor
from llm_memory.conversation.processors import ProcessorPipeline
from llm_memory.storage.memory import MemoryStorage


def main() -> None:
    memory = ConversationMemory(storage=MemoryStorage())

    memory.add_message("thread-rag", "system", "You are helpful.")
    memory.add_message("thread-rag", "user", "Explain reranking.")
    memory.add_message(
        "thread-rag",
        "assistant",
        "Reranking sorts retrieved documents.",
    )
    memory.add_message("thread-rag", "tool", "Tool output here.")
    memory.add_message("thread-rag", "user", "What is a cross-encoder?")

    messages = memory.get_messages("thread-rag")

    processor = ProcessorPipeline(
        processors=[
            FilterByRoleProcessor(allowed_roles={"user", "assistant"}),
            KeepRecentMessagesProcessor(max_messages=3),
        ]
    )

    messages_for_model = processor.process(messages)

    for message in messages_for_model:
        print(message.role, message.content)


if __name__ == "__main__":
    main()
