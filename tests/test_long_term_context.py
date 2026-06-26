from __future__ import annotations

from agent_memory.context.formatters import BulletListFormatter
from agent_memory.context.formatters import XMLBlockFormatter
from agent_memory.context.interface import MemoryContextRequest
from agent_memory.context.long_term import LongTermMemoryContextBuilder
from agent_memory.context.long_term import format_grouped_records
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.retrieval.lexical import LexicalMemoryRetriever


def test_format_grouped_records_groups_memory_by_type() -> None:
    records = [
        KnowledgeMemory(
            id="fact",
            namespace=("user", "default"),
            key="timezone",
            content="User works in the Africa/Nairobi timezone.",
        ),
        PreferenceMemory(
            id="preference",
            namespace=("user", "default"),
            key="tone",
            subject="response style",
            preference="concise but warm",
        ),
        EntityMemory(
            id="entity",
            namespace=("user", "default"),
            key="project",
            name="agent-memory",
            description="A reusable memory library for agent SDKs.",
        ),
    ]

    content = format_grouped_records(records)

    assert content == "\n".join(
        [
            "Relevant long-term memory:",
            "",
            "Known facts:",
            "- User works in the Africa/Nairobi timezone.",
            "",
            "Known preferences:",
            "- response style: concise but warm",
            "",
            "Known entities:",
            "- agent-memory: A reusable memory library for agent SDKs.",
        ]
    )


def test_long_term_context_builder_uses_custom_type_headings() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(storage=storage, retrievers=[LexicalMemoryRetriever()])
    namespace = ("user", "default")
    store.put(
        KnowledgeMemory(
            id="fact",
            namespace=namespace,
            key="timezone",
            content="User works in the Africa/Nairobi timezone.",
        )
    )
    builder = LongTermMemoryContextBuilder(
        memory_store=store,
        type_headings={"semantic": "Facts to use"},
    )

    result = builder.build(
        MemoryContextRequest(namespace=namespace, query="timezone")
    )

    assert result.content == "\n".join(
        [
            "Relevant long-term memory:",
            "",
            "Facts to use:",
            "- User works in the Africa/Nairobi timezone.",
        ]
    )
    assert result.record_ids == ["fact"]


def test_long_term_context_builder_uses_custom_formatter() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(storage=storage, retrievers=[LexicalMemoryRetriever()])
    namespace = ("user", "default")
    store.put(
        KnowledgeMemory(
            id="fact",
            namespace=namespace,
            key="timezone",
            content="User works in the Africa/Nairobi timezone.",
        )
    )
    builder = LongTermMemoryContextBuilder(
        memory_store=store,
        formatter=BulletListFormatter(heading="Memory"),
    )

    result = builder.build(
        MemoryContextRequest(namespace=namespace, query="timezone")
    )

    assert result.content == "\n".join(
        [
            "Memory:",
            "- User works in the Africa/Nairobi timezone.",
        ]
    )


def test_xml_block_formatter_escapes_record_content() -> None:
    formatter = XMLBlockFormatter()
    content = formatter.format(
        [
            KnowledgeMemory(
                id="fact",
                namespace=("user", "default"),
                key="language",
                content="User likes Python & TypeScript.",
            )
        ]
    )

    assert content == "\n".join(
        [
            "<memory>",
            (
                '  <item id="fact" type="semantic" key="language">'
                "User likes Python &amp; TypeScript."
                "</item>"
            ),
            "</memory>",
        ]
    )
