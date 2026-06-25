from __future__ import annotations

from rank_bm25 import BM25Okapi

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.search import MemorySearch
from agent_memory.long_term.search import RetrievalResult
from agent_memory.retrieval._matching import blend_importance
from agent_memory.retrieval._matching import record_matches_search
from agent_memory.retrieval._matching import searchable_text
from agent_memory.retrieval._matching import token_overlap_score
from agent_memory.retrieval._matching import tokenize_terms


class LexicalMemoryRetriever:
    def __init__(self) -> None:
        self._records: dict[str, LongTermRecord] = {}

    def add(self, record: LongTermRecord) -> None:
        self._records[record.id] = record

    def search(self, search: MemorySearch) -> list[RetrievalResult]:
        records: list[LongTermRecord] = []
        corpus: list[list[str]] = []

        for record in self._records.values():
            if not record_matches_search(record, search):
                continue

            records.append(record)
            corpus.append(tokenize_terms(searchable_text(record)))

        query_tokens = tokenize_terms(search.query)

        if not records or not query_tokens:
            return []

        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)
        scored_records: list[tuple[float, LongTermRecord]] = [
            (float(score), record)
            for score, record in zip(scores, records)
            if score > 0
        ]

        if not scored_records:
            scored_records = [
                (
                    token_overlap_score(search.query, [searchable_text(record)]),
                    record,
                )
                for record in records
            ]
            scored_records = [
                (score, record)
                for score, record in scored_records
                if score > 0
            ]
        else:
            max_score = max(score for score, _ in scored_records)
            scored_records = [
                (score / max_score, record)
                for score, record in scored_records
            ]

        scored_records.sort(key=lambda scored_record: scored_record[0], reverse=True)
        return [
            RetrievalResult(
                record_id=record.id,
                source="lexical",
                score=blend_importance(score, record),
                relevance_score=score,
                importance_score=record.importance,
                reason="ranked record text with BM25 lexical search",
            )
            for score, record in scored_records[: search.limit]
        ]

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)
