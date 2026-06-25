from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.retrieval.episodic import EpisodicMemoryRetriever


def test_episodic_retriever_scores_are_normalized() -> None:
    retriever = EpisodicMemoryRetriever()
    namespace = ("user", "default")
    retriever.add(
        EventMemory(
            id="event",
            namespace=namespace,
            key="launch",
            description="launched the memory system",
            occurred_at=datetime.now(timezone.utc),
            importance=1.0,
        )
    )

    results = retriever.search(
        MemorySearch(namespace=namespace, query="launched memory system")
    )

    assert len(results) == 1
    assert results[0].relevance_score is not None
    assert results[0].recency_score is not None
    assert 0 <= results[0].relevance_score <= 1
    assert 0 <= results[0].recency_score <= 1
    assert 0 <= results[0].score <= 1


def test_memory_store_search_uses_rank_fusion_across_retrievers() -> None:
    storage = InMemoryStorage()
    namespace = ("user", "default")
    single_hit = KnowledgeMemory(
        id="single-hit",
        namespace=namespace,
        key="single",
        content="single retriever result",
    )
    shared_hit = KnowledgeMemory(
        id="shared-hit",
        namespace=namespace,
        key="shared",
        content="shared retriever result",
    )
    storage.put(single_hit)
    storage.put(shared_hit)
    store = MemoryStore(
        storage=storage,
        retrievers=[
            StaticRetriever(
                [
                    result("single-hit", 1.0),
                    result("shared-hit", 0.9),
                ]
            ),
            StaticRetriever(
                [
                    result("shared-hit", 0.1),
                ]
            ),
        ],
    )

    records = store.search(namespace=namespace, query="anything", limit=2)

    assert [record.id for record in records] == ["shared-hit", "single-hit"]


def result(record_id: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        record_id=record_id,
        source="test",
        score=score,
    )


@dataclass
class StaticRetriever:
    results: list[RetrievalResult]

    def add(self, record: LongTermRecord) -> None:
        pass

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        return self.results

    def delete(self, record_id: str) -> None:
        pass
