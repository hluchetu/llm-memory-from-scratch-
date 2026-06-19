from __future__ import annotations

from agent_memory.context.conversation.memory import ConversationMemory
from agent_memory.context.conversation.processors import ProcessingContext
from agent_memory.context.conversation.processors import SummarizeOldMessagesProcessor
from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import Message as LLMMessage
from agent_memory.storage.memory import MemoryStorage


class FakeSummaryModel:
    def invoke(self, messages: list[LLMMessage]) -> AIMessage:
        return AIMessage(
            content=(
                "The user is building a production-style LLM memory system. "
                "They want raw messages preserved and summaries stored as derived context."
            )
        )


def main() -> None:
    memory = ConversationMemory(storage=MemoryStorage())

    memory.add_message(
        thread_id="thread-rag",
        role="user",
        content="I am building an LLM memory system.",
    )
    memory.add_message(
        thread_id="thread-rag",
        role="assistant",
        content="Keep raw messages as the source of truth.",
    )
    memory.add_message(
        thread_id="thread-rag",
        role="user",
        content="Summaries should be derived context.",
    )
    memory.add_message(
        thread_id="thread-rag",
        role="assistant",
        content="That keeps auditability and cheaper model context.",
    )

    processor = SummarizeOldMessagesProcessor(
        model=FakeSummaryModel(),
        trigger_message_count=4,
        keep_recent_messages=2,
    )

    model_context = processor.process(
        messages=memory.get_messages("thread-rag"),
        context=ProcessingContext(),
    )

    summary_message = model_context[0]
    covered_item_ids = summary_message.metadata["covered_item_ids"]

    if not isinstance(covered_item_ids, list):
        raise TypeError("covered_item_ids must be a list.")

    memory.add_summary(
        thread_id="thread-rag",
        content=summary_message.content.removeprefix(
            "Conversation summary so far:\n"
        ),
        covered_item_ids=covered_item_ids,
        metadata={
            "source": "summarize_old_messages_processor",
        },
    )

    for item in memory.get_items("thread-rag"):
        print(item.item_type)
        print(item.content)
        print()


if __name__ == "__main__":
    main()
