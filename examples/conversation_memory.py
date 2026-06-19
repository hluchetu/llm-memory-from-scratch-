from __future__ import annotations

from agent_memory.context.conversation.memory import ConversationMemory
from agent_memory.context.conversation.processors import FilterByRoleProcessor
from agent_memory.context.conversation.processors import KeepWithinTokenBudgetProcessor
from agent_memory.context.conversation.processors import ProcessorPipeline
from agent_memory.context.conversation.state import Message
from agent_memory.storage.memory import MemoryStorage


class WhitespaceTokenCounter:
    def count_message(self, message: Message) -> int:
        return len(message.content.split()) + 1


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
            KeepWithinTokenBudgetProcessor(
                max_tokens=12,
                token_counter=WhitespaceTokenCounter(),
            ),
        ]
    )

    messages_for_model = processor.process(messages)

    for message in messages_for_model:
        print(message.role, message.content)


if __name__ == "__main__":
    main()
