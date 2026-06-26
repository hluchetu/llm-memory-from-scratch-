from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_memory.context.interface import MemoryContextRequest
from agent_memory.context.long_term import LongTermMemoryContextBuilder
from agent_memory.extraction.interface import MemoryExtractionRequest
from agent_memory.extraction.llm import LLMMemoryExtractor
from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import Message as LLMMessage
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.manager import MemoryManager
from agent_memory.manager import MemoryStoreConfig
from agent_memory.reflection import MemoryReflector
from agent_memory.retrieval.lexical import LexicalMemoryRetriever
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message


@pytest.mark.asyncio
async def test_memory_store_async_methods() -> None:
    store = MemoryStore(
        storage=InMemoryStorage(),
        retrievers=[LexicalMemoryRetriever()],
    )
    namespace = ("user", "default")
    record = PreferenceMemory(
        id="preference",
        namespace=namespace,
        key="tone",
        subject="response tone",
        preference="concise but warm",
    )

    await store.put_async(record)

    assert await store.get_async(namespace, "tone") == record
    assert await store.list_async(namespace, memory_type="preference") == [record]
    assert [
        result.id
        for result in await store.search_async(namespace, "concise warm")
    ] == ["preference"]
    assert await store.invalidate_async(namespace, "tone") is True
    assert await store.search_async(namespace, "concise warm") == []

    await store.delete_async(namespace, "tone")

    assert await store.get_async(namespace, "tone") is None


@pytest.mark.asyncio
async def test_long_term_context_builder_build_async() -> None:
    store = MemoryStore(
        storage=InMemoryStorage(),
        retrievers=[LexicalMemoryRetriever()],
    )
    namespace = ("user", "default")
    store.put(
        KnowledgeMemory(
            id="fact",
            namespace=namespace,
            key="timezone",
            content="User works in the Africa/Nairobi timezone.",
        )
    )
    builder = LongTermMemoryContextBuilder(memory_store=store)

    result = await builder.build_async(
        MemoryContextRequest(namespace=namespace, query="timezone")
    )

    assert result.has_content
    assert result.record_ids == ["fact"]


@pytest.mark.asyncio
async def test_llm_memory_extractor_extract_async() -> None:
    extractor = LLMMemoryExtractor(
        model=StaticModel(
            response='{"records":[{"action":"create","record_type":"preference","key":"tone","subject":"response tone","preference":"concise but warm","importance":0.8}]}'
        )
    )
    request = MemoryExtractionRequest(
        namespace=("user", "default"),
        conversation=ConversationState(
            thread_id="thread",
            items=[
                Message(
                    id="message",
                    role="user",
                    content="Please keep responses concise but warm.",
                )
            ],
        ),
    )

    result = await extractor.extract_async(request)

    assert len(result.records) == 1
    assert result.records[0].key == "tone"
    assert result.source_item_ids == ["message"]


@pytest.mark.asyncio
async def test_memory_reflector_async_methods() -> None:
    store = MemoryStore(storage=InMemoryStorage(), max_related_ids=0)
    namespace = ("user", "default")
    source = KnowledgeMemory(
        id="source",
        namespace=namespace,
        key="source",
        content="The user prefers reusable agent memory primitives.",
        importance=1.0,
    )
    store.put(source)
    reflector = MemoryReflector(
        memory_store=store,
        model=StaticModel(
            response='{"insights":[{"key":"insight","content":"The user values reusable memory primitives.","importance":0.8,"supporting_keys":["source"]}]}'
        ),
        reflection_interval=99,
        importance_threshold=1.0,
    )

    observed = await reflector.observe_async([source], namespace)

    assert observed is not None
    assert await store.get_async(namespace, "insight") is not None

    reflected = await reflector.reflect_async(namespace)

    assert reflected.source_record_ids


@pytest.mark.asyncio
async def test_memory_manager_async_methods() -> None:
    store = MemoryStore(
        storage=InMemoryStorage(),
        retrievers=[LexicalMemoryRetriever()],
    )
    namespace = ("user", "default")
    await store.put_async(
        KnowledgeMemory(
            id="fact",
            namespace=namespace,
            key="timezone",
            content="User works in the Africa/Nairobi timezone.",
        )
    )
    manager = MemoryManager(
        stores=[
            MemoryStoreConfig(
                name="default",
                description="Default memory store",
                store=store,
            )
        ],
    )

    context = await manager.inject_async("timezone", namespace)
    records = await manager.search_async("timezone", namespace)
    extraction = await manager.extract_async(
        ConversationState(thread_id="thread"),
        namespace,
    )

    assert context.has_content
    assert [record.id for record in records] == ["fact"]
    assert extraction.skipped_reason == "No extractor configured."


@dataclass
class StaticModel:
    response: str

    def invoke(self, messages: list[LLMMessage]) -> AIMessage:
        return AIMessage(content=self.response)
