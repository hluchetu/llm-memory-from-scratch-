from __future__ import annotations

from dataclasses import dataclass

from agent_memory.llm.message import AIMessage
from agent_memory.llm.message import Message
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.reflection import MemoryReflector
from agent_memory.reflection import select_reflection_sources


def test_memory_reflector_writes_reflection_insights() -> None:
    store = MemoryStore(storage=InMemoryStorage(), max_related_ids=0)
    namespace = ("user", "default")
    store.put(
        PreferenceMemory(
            id="tone",
            namespace=namespace,
            key="tone",
            subject="response tone",
            preference="concise but warm",
            importance=0.8,
        )
    )
    store.put(
        KnowledgeMemory(
            id="sdk",
            namespace=namespace,
            key="sdk-focus",
            content="The user is building a memory library for agent SDKs.",
            importance=0.7,
        )
    )
    reflector = MemoryReflector(
        memory_store=store,
        model=StaticModel(
            response='{"insights":[{"key":"user-values-sdk-memory","content":"The user values reusable memory primitives for agent SDKs and prefers concise warm explanations.","importance":0.9,"supporting_keys":["tone","sdk-focus"]}]}'
        ),
    )

    result = reflector.reflect(namespace)

    assert result.skipped_reason is None
    assert len(result.records) == 1
    stored = store.get(namespace, "user-values-sdk-memory")
    assert stored is not None
    assert isinstance(stored, KnowledgeMemory)
    assert stored.source == "reflection"
    assert stored.importance == 0.9
    assert stored.metadata["source"] == "reflection"
    assert stored.metadata["supporting_keys"] == ["tone", "sdk-focus"]
    assert stored.metadata["supporting_record_ids"] == ["tone", "sdk"]
    assert stored.related_ids == ("tone", "sdk")


def test_memory_reflector_observe_triggers_after_importance_threshold() -> None:
    store = MemoryStore(storage=InMemoryStorage(), max_related_ids=0)
    namespace = ("user", "default")
    source = KnowledgeMemory(
        id="source",
        namespace=namespace,
        key="source",
        content="Important source memory.",
        importance=1.0,
    )
    store.put(source)
    reflector = MemoryReflector(
        memory_store=store,
        model=StaticModel(
            response='{"insights":[{"key":"insight","content":"A reflected insight.","importance":0.8,"supporting_keys":["source"]}]}'
        ),
        reflection_interval=99,
        importance_threshold=1.0,
    )

    result = reflector.observe([source], namespace)

    assert result is not None
    assert store.get(namespace, "insight") is not None


def test_select_reflection_sources_excludes_existing_reflections() -> None:
    raw = KnowledgeMemory(
        id="raw",
        namespace=("user", "default"),
        key="raw",
        content="Raw memory.",
        importance=0.5,
    )
    reflection = KnowledgeMemory(
        id="reflection",
        namespace=("user", "default"),
        key="reflection",
        content="Existing reflection.",
        source="reflection",
        metadata={"source": "reflection"},
        importance=1.0,
    )

    assert select_reflection_sources([reflection, raw], limit=10) == [raw]


@dataclass
class StaticModel:
    response: str

    def invoke(self, messages: list[Message]) -> AIMessage:
        return AIMessage(content=self.response)
