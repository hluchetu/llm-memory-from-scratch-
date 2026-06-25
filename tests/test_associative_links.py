from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.serialization import record_from_dict
from agent_memory.long_term.serialization import record_to_dict
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.retrieval.lexical import LexicalMemoryRetriever
from agent_memory.retrieval.semantic import SemanticMemoryRetriever
from agent_memory.vector_store import VectorSearchResult


def test_record_serialization_preserves_related_ids() -> None:
    record = KnowledgeMemory(
        id="memory",
        namespace=("user", "default"),
        key="project",
        content="The agent-memory project uses typed long-term memory records.",
        related_ids=("related-a", "related-b"),
    )

    restored = record_from_dict(record_to_dict(record))

    assert restored.related_ids == ("related-a", "related-b")


def test_memory_store_links_related_records_on_write() -> None:
    storage = InMemoryStorage()
    store = MemoryStore(
        storage=storage,
        retrievers=[LexicalMemoryRetriever()],
    )
    namespace = ("user", "default")
    first = KnowledgeMemory(
        id="first",
        namespace=namespace,
        key="agent-memory-library",
        content="Agent memory is a reusable library for agent SDKs.",
    )
    second = KnowledgeMemory(
        id="second",
        namespace=namespace,
        key="agent-memory-retrieval",
        content="Agent memory retrieval combines BM25 and semantic search.",
    )

    store.put(first)
    store.put(second)

    stored_first = storage.get_by_id("first")
    stored_second = storage.get_by_id("second")

    assert stored_first is not None
    assert stored_second is not None
    assert stored_second.related_ids == ("first",)
    assert stored_first.related_ids == ("second",)


def test_semantic_retriever_includes_one_hop_related_records() -> None:
    storage = InMemoryStorage()
    parent = KnowledgeMemory(
        id="parent",
        namespace=("user", "default"),
        key="agent-memory",
        content="Agent memory supports retrieval.",
        related_ids=("related",),
    )
    related = KnowledgeMemory(
        id="related",
        namespace=("user", "default"),
        key="bm25",
        content="BM25 improves lexical retrieval.",
    )
    storage.put(parent)
    storage.put(related)
    retriever = SemanticMemoryRetriever(
        embedder=StaticEmbedder(),
        vector_store=StaticVectorStore(
            results=[
                VectorSearchResult(record_id="parent", score=0.8),
            ]
        ),
        storage=storage,
    )

    results = retriever.search(
        MemorySearch(
            namespace=("user", "default"),
            query="memory retrieval",
            limit=2,
        )
    )

    assert [result.record_id for result in results] == ["parent", "related"]
    assert results[1].reason == "one-hop related memory from semantic match parent"
    assert results[1].relevance_score == 0.7200000000000001


class StaticEmbedder:
    def embed(self, text: str) -> list[float]:
        return [1.0]


@dataclass
class StaticVectorStore:
    results: list[VectorSearchResult]

    def upsert(
        self,
        record_id: str,
        vector: list[float],
        document: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    def search(
        self,
        vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        return self.results[:limit]

    def delete(self, record_id: str) -> None:
        pass
