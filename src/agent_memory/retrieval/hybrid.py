from __future__ import annotations

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.retriever import MemoryRetriever
from agent_memory.long_term.ranking import reciprocal_rank_score
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult


class HybridMemoryRetriever:
    def __init__(
        self,
        retrievers: list[MemoryRetriever],
        routes: dict[str | None, list[MemoryRetriever]] | None = None,
    ) -> None:
        self._retrievers = retrievers
        self._routes = routes

    def add(self, record: LongTermRecord) -> None:
        for retriever in self._retrievers:
            retriever.add(record)

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        rrf_scores_by_record_id: dict[str, float] = {}
        best_results_by_record_id: dict[str, RetrievalResult] = {}
        selected_retrievers = self._select_retrievers(search)

        for retriever in selected_retrievers:
            results = retriever.search(search)

            for rank, result in enumerate(results, start=1):
                rrf_scores_by_record_id[result.record_id] = (
                    rrf_scores_by_record_id.get(result.record_id, 0.0)
                    + reciprocal_rank_score(rank)
                )

                current_result = best_results_by_record_id.get(result.record_id)

                if current_result is not None and current_result.score >= result.score:
                    best_results_by_record_id[result.record_id] = current_result
                else:
                    best_results_by_record_id[result.record_id] = result

        fused_results = [
            RetrievalResult(
                record_id=record_id,
                source=best_result.source,
                score=rrf_score,
                relevance_score=best_result.relevance_score,
                recency_score=best_result.recency_score,
                importance_score=best_result.importance_score,
                reason=best_result.reason,
            )
            for record_id, rrf_score in rrf_scores_by_record_id.items()
            for best_result in [best_results_by_record_id[record_id]]
        ]

        fused_results.sort(
            key=lambda result: result.score,
            reverse=True,
        )
        return fused_results[: search.limit]

    def delete(self, record_id: str) -> None:
        for retriever in self._retrievers:
            retriever.delete(record_id)

    def _select_retrievers(self, search: MemorySearch) -> list[MemoryRetriever]:
        if self._routes is None:
            return self._retrievers

        if search.memory_type in self._routes:
            return self._routes[search.memory_type]

        return self._routes.get(None, self._retrievers)
