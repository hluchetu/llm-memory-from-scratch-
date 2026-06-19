from __future__ import annotations

from agent_memory.context.conversation.memory import ConversationMemory
from agent_memory.context.conversation.state import Message
from agent_memory.context.conversation.state import SummaryItem
from agent_memory.storage.memory import MemoryStorage


def main() -> None:
    memory = ConversationMemory(storage=MemoryStorage())

    first_message = memory.add_message(
        thread_id="thread-rag",
        role="user",
        content="I am building an LLM memory system.",
    )
    second_message = memory.add_message(
        thread_id="thread-rag",
        role="assistant",
        content="Separate context modeling from storage.",
    )
    memory.add_message(
        thread_id="thread-rag",
        role="user",
        content="Keep raw messages, but summarize older context.",
    )

    memory.add_summary(
        thread_id="thread-rag",
        content=(
            "The conversation is about building an LLM memory system. "
            "Raw messages should remain stored, while summaries are derived context."
        ),
        covered_item_ids=[
            first_message.id,
            second_message.id,
        ],
        metadata={
            "source": "manual_example",
        },
    )

    items = memory.get_items("thread-rag")

    for item in items:
        print(item.item_type)

        if isinstance(item, Message):
            print(item.content)
        elif isinstance(item, SummaryItem):
            print(item.content)
            print(item.covered_item_ids)

        print()


if __name__ == "__main__":
    main()
