from __future__ import annotations

import pytest

from agent_memory.errors import NamespaceAccessError
from agent_memory.long_term.policy import NamespacePrefixPolicy
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.retrieval.lexical import LexicalMemoryRetriever


def test_memory_store_allows_matching_namespace_prefix() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(
        storage=storage,
        retrievers=[LexicalMemoryRetriever()],
        namespace_policy=NamespacePrefixPolicy(("user", "alice")),
    )
    record = KnowledgeMemory(
        id="memory",
        namespace=("user", "alice"),
        key="timezone",
        content="Alice works in the Africa/Nairobi timezone.",
    )

    store.put(record)

    assert store.get(("user", "alice"), "timezone") == record
    assert store.list(("user", "alice")) == [record]
    assert store.search(("user", "alice"), "timezone") == [record]


def test_memory_store_rejects_cross_namespace_reads() -> None:
    storage = InMemoryStorage()
    storage.put(
        KnowledgeMemory(
            id="memory",
            namespace=("user", "bob"),
            key="timezone",
            content="Bob works in UTC.",
        )
    )
    store = MemoryStore(
        storage=storage,
        namespace_policy=NamespacePrefixPolicy(("user", "alice")),
    )

    with pytest.raises(NamespaceAccessError, match="Read access denied"):
        store.get(("user", "bob"), "timezone")

    with pytest.raises(NamespaceAccessError, match="Read access denied"):
        store.list(("user", "bob"))

    with pytest.raises(NamespaceAccessError, match="Read access denied"):
        store.search(("user", "bob"), "timezone")


def test_memory_store_rejects_cross_namespace_writes() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(
        storage=storage,
        namespace_policy=NamespacePrefixPolicy(("user", "alice")),
    )
    record = KnowledgeMemory(
        id="memory",
        namespace=("user", "bob"),
        key="timezone",
        content="Bob works in UTC.",
    )

    with pytest.raises(NamespaceAccessError, match="Write access denied"):
        store.put(record)

    assert storage.get(("user", "bob"), "timezone") is None


def test_memory_store_rejects_invalidate_and_delete_without_write_access() -> None:
    storage = InMemoryStorage()
    record = KnowledgeMemory(
        id="memory",
        namespace=("user", "bob"),
        key="timezone",
        content="Bob works in UTC.",
    )
    storage.put(record)
    store = MemoryStore(
        storage=storage,
        namespace_policy=NamespacePrefixPolicy(("user", "alice")),
    )

    with pytest.raises(NamespaceAccessError, match="Write access denied"):
        store.invalidate(("user", "bob"), "timezone")

    with pytest.raises(NamespaceAccessError, match="Write access denied"):
        store.delete(("user", "bob"), "timezone")

    assert storage.get(("user", "bob"), "timezone") == record


def test_namespace_policy_can_be_read_only() -> None:
    storage = InMemoryStorage()
    record = KnowledgeMemory(
        id="memory",
        namespace=("user", "alice"),
        key="timezone",
        content="Alice works in the Africa/Nairobi timezone.",
    )
    storage.put(record)
    store = MemoryStore(
        storage=storage,
        namespace_policy=NamespacePrefixPolicy(
            ("user", "alice"),
            allow_writes=False,
        ),
    )

    assert store.get(("user", "alice"), "timezone") == record

    with pytest.raises(NamespaceAccessError, match="Write access denied"):
        store.put(
            KnowledgeMemory(
                id="new",
                namespace=("user", "alice"),
                key="language",
                content="Alice uses Python.",
            )
        )
