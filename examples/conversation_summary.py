from __future__ import annotations

from llm_memory.context.conversation.processors import ProcessingContext
from llm_memory.context.conversation.processors import SummarizeOldMessagesProcessor
from llm_memory.context.conversation.state import Message
from llm_memory.llm.message import AIMessage
from llm_memory.llm.message import Message as LLMMessage


class FakeSummaryModel:
    def invoke(self, messages: list[LLMMessage]) -> AIMessage:
        return AIMessage(
            content=(
                "The user is building an LLM memory system. "
                "They prefer production-style architecture, explicit types, "
                "and reusable patterns across repos."
            )
        )


def main() -> None:
    messages = [
        Message(
            role="user",
            content="I am building an LLM memory repo.",
        ),
        Message(
            role="assistant",
            content="Good. We should separate context from storage.",
        ),
        Message(
            role="user",
            content="I like explicit types and reusable patterns.",
        ),
        Message(
            role="assistant",
            content="Then the model boundary should be messages in, AIMessage out.",
        ),
        Message(
            role="user",
            content="Now explain summary memory.",
        ),
    ]

    processor = SummarizeOldMessagesProcessor(
        model=FakeSummaryModel(),
        trigger_message_count=5,
        keep_recent_messages=2,
    )

    processed_messages = processor.process(
        messages=messages,
        context=ProcessingContext(),
    )

    for message in processed_messages:
        print(message.role)
        print(message.content)
        print(message.metadata)
        print()


if __name__ == "__main__":
    main()

