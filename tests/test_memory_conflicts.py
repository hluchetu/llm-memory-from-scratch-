from __future__ import annotations

from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.retrieval.lexical import LexicalMemoryRetriever


def test_put_invalidates_conflicting_preference_records() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(storage=storage, retrievers=[LexicalMemoryRetriever()])
    namespace = ("user", "default")
    stale = PreferenceMemory(
        id="stale",
        namespace=namespace,
        key="drink-tea",
        subject="preferred drink",
        preference="green tea",
    )
    fresh = PreferenceMemory(
        id="fresh",
        namespace=namespace,
        key="drink-coffee",
        subject="preferred drink",
        preference="black coffee",
    )

    store.put(stale)
    store.put(fresh)

    stale_record = storage.get(namespace, "drink-tea")
    fresh_record = storage.get(namespace, "drink-coffee")

    assert stale_record is not None
    assert stale_record.invalidated_at is not None
    assert fresh_record is not None
    assert fresh_record.invalidated_at is None
    assert store.search(namespace=namespace, query="green tea") == []
    assert [record.id for record in store.search(namespace=namespace, query="coffee")] == [
        "fresh"
    ]


def test_put_keeps_matching_preference_records_active() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(storage=storage)
    namespace = ("user", "default")
    first = PreferenceMemory(
        id="first",
        namespace=namespace,
        key="drink-tea",
        subject="preferred drink",
        preference="green tea",
    )
    duplicate = PreferenceMemory(
        id="duplicate",
        namespace=namespace,
        key="drink-tea-copy",
        subject="preferred drink",
        preference="green tea",
    )

    store.put(first)
    store.put(duplicate)

    active_ids = {
        record.id
        for record in storage.list(namespace=namespace, memory_type="preference")
    }

    assert active_ids == {"first", "duplicate"}


def test_invalidate_removes_record_from_search_results() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(storage=storage, retrievers=[LexicalMemoryRetriever()])
    namespace = ("user", "default")
    record = PreferenceMemory(
        id="memory",
        namespace=namespace,
        key="drink-tea",
        subject="preferred drink",
        preference="green tea",
    )

    store.put(record)

    assert store.search(namespace=namespace, query="green tea")

    assert store.invalidate(namespace, "drink-tea") is True

    invalidated = storage.get(namespace, "drink-tea")
    assert invalidated is not None
    assert invalidated.invalidated_at is not None
    assert store.search(namespace=namespace, query="green tea") == []
