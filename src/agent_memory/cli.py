from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from agent_memory.agent import Agent
from agent_memory.agent import AgentRunner
from agent_memory.agent import AgentSession
from agent_memory.context import LongTermMemoryContextBuilder
from agent_memory.extraction import LLMMemoryExtractor
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import SummaryItem
from agent_memory.main import create_chat_model
from agent_memory.main import create_conversation_memory
from agent_memory.retrieval.factory import create_memory_store


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    memory = create_conversation_memory(database_path=args.database_path)

    if args.command == "chat":
        try:
            model = create_chat_model()
        except RuntimeError as error:
            parser.exit(1, f"error: {error}\n")

        namespace = args.namespace
        memory_store = create_memory_store() if namespace is not None else None
        context_builder = (
            LongTermMemoryContextBuilder(memory_store)
            if memory_store is not None
            else None
        )
        extractor = (
            LLMMemoryExtractor(model)
            if memory_store is not None
            else None
        )
        runner = AgentRunner(
            conversation_memory=memory,
            memory_store=memory_store,
            context_builder=context_builder,
            extractor=extractor,
        )
        agent = Agent(
            name="agent-memory-cli",
            instructions="You are a helpful assistant with access to conversation memory.",
            model=model,
        )
        session = AgentSession(
            thread_id=args.thread_id,
            namespace=namespace,
        )

        print(f"Thread: {args.thread_id}")
        if namespace is not None:
            print(f"Namespace: {'/'.join(namespace)}")
        print("Type 'exit' or 'quit' to stop.")

        while True:
            user_input = input("you> ").strip()

            if user_input.lower() in {"exit", "quit"}:
                return 0

            if not user_input:
                continue

            result = runner.run(
                agent=agent,
                session=session,
                user_input=user_input,
            )
            print(f"assistant> {result.raw_output}")

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
    chat.add_argument(
        "--namespace",
        type=parse_namespace,
        default=None,
        help="Optional long-term memory namespace, written as user/hayat or project/name.",
    )

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


def parse_namespace(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None

    parts = tuple(
        part.strip()
        for part in value.split("/")
        if part.strip()
    )

    if not parts:
        raise argparse.ArgumentTypeError("namespace must not be empty")

    return parts


def format_item(item: object) -> str:
    if isinstance(item, Message):
        return f"{item.created_at.isoformat()}  {item.role}: {item.content}"

    if isinstance(item, SummaryItem):
        return f"{item.created_at.isoformat()}  summary: {item.content}"

    return str(item)
