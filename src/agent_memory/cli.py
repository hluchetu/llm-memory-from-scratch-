from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from agent_memory.context.conversation.state import Message
from agent_memory.context.conversation.state import SummaryItem
from agent_memory.llm.adapters import to_llm_messages
from agent_memory.main import create_chat_model
from agent_memory.main import create_conversation_memory


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    memory = create_conversation_memory(database_path=args.database_path)

    if args.command == "chat":
        try:
            model = create_chat_model()
        except RuntimeError as error:
            parser.exit(1, f"error: {error}\n")

        print(f"Thread: {args.thread_id}")
        print("Type 'exit' or 'quit' to stop.")

        while True:
            user_input = input("you> ").strip()

            if user_input.lower() in {"exit", "quit"}:
                return 0

            if not user_input:
                continue

            memory.add_message(
                thread_id=args.thread_id,
                role="user",
                content=user_input,
            )
            messages = memory.get_messages(args.thread_id)
            response = model.invoke(to_llm_messages(messages))
            memory.add_message(
                thread_id=args.thread_id,
                role="assistant",
                content=response.content,
                model_name=response.metadata.get("model"),
                usage=response.usage,
                metadata=response.metadata,
            )
            print(f"assistant> {response.content}")

    if args.command == "show-thread":
        items = memory.get_items(args.thread_id)

        if not items:
            print(f"No conversation items found for {args.thread_id}")
            return 0

        for item in items:
            print(format_item(item))

        return 0

    if args.command == "clear-thread":
        memory.clear_thread(args.thread_id)
        print(f"Cleared thread {args.thread_id}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory",
        description="Run a memory-backed agent chat.",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to AGENT_MEMORY_SQLITE_DATABASE_PATH or .memory/conversations.db.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    chat = subparsers.add_parser(
        "chat",
        help="Start an interactive memory-backed chat.",
    )
    chat.add_argument("thread_id")

    show_thread = subparsers.add_parser(
        "show-thread",
        help="Print the stored items for a conversation thread.",
    )
    show_thread.add_argument("thread_id")

    clear_thread = subparsers.add_parser(
        "clear-thread",
        help="Delete a conversation thread.",
    )
    clear_thread.add_argument("thread_id")

    return parser


def format_item(item: object) -> str:
    if isinstance(item, Message):
        return f"{item.created_at.isoformat()}  {item.role}: {item.content}"

    if isinstance(item, SummaryItem):
        return f"{item.created_at.isoformat()}  summary: {item.content}"

    return str(item)
