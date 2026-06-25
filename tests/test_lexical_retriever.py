from __future__ import annotations

from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.semantic.knowledge import KnowledgeMemory
from agent_memory.retrieval.lexical import LexicalMemoryRetriever


def test_lexical_retriever_ranks_with_bm25_term_specificity() -> None:
    retriever = LexicalMemoryRetriever()
    namespace = ("user", "default")
    common_match = KnowledgeMemory(
        id="common",
        namespace=namespace,
        key="food-common",
        content="sushi lunch dinner",
    )
    rare_match = KnowledgeMemory(
        id="rare",
        namespace=namespace,
        key="food-rare",
        content="saffron rice preference",
    )
    another_common_match = KnowledgeMemory(
        id="another-common",
        namespace=namespace,
        key="food-another-common",
        content="sushi calendar",
    )
    unrelated = KnowledgeMemory(
        id="unrelated",
        namespace=namespace,
        key="music",
        content="sushi jazz piano playlist",
    )

    retriever.add(common_match)
    retriever.add(rare_match)
    retriever.add(another_common_match)
    retriever.add(unrelated)

    results = retriever.search(
        MemorySearch(namespace=namespace, query="sushi saffron", limit=4)
    )

    assert results[0].record_id == "rare"
    assert results[0].source == "lexical"
    assert results[0].relevance_score is not None
    assert results[0].relevance_score > results[1].relevance_score
    assert results[0].reason == "ranked record text with BM25 lexical search"


def test_lexical_retriever_returns_empty_results_for_empty_query() -> None:
    retriever = LexicalMemoryRetriever()
    retriever.add(
        KnowledgeMemory(
            id="memory",
            namespace=("user", "default"),
            key="food",
            content="user likes sushi",
        )
    )

    results = retriever.search(
        MemorySearch(namespace=("user", "default"), query="   ", limit=2)
    )

    assert results == []
