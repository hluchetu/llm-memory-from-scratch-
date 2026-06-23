# Memory Retrieval

Retrieval decides which saved memories should be brought back into the agent context.

The important principle:

> Storage keeps memory durable. Retrieval decides what is relevant right now.

A serious memory system does not retrieve every memory the same way. Semantic facts, entities, events, and workflows have different access patterns, so they need different retrieval strategies.

## Search Request

Retrieval is represented by a `MemorySearch` request:

```
namespace   — where to search
query       — what the agent is looking for
memory_type — optional record type filter
limit       — maximum number of records to return
metadata    — exact field, tag, and creation-time filters
```

Example:

```python
from agent_memory.long_term import MetadataFilter

records = memory.search(
    namespace=("bank", "customer-123"),
    query="card alerts",
    memory_type="semantic",
    metadata=MetadataFilter(
        equals={"region": "KE"},
        contains_all_tags={"cards"},
    ),
)
```

This means:

```
Search customer-123 banking memories
Only semantic records
Only records from region KE
Only records tagged cards
Return the most relevant matches for "card alerts"
```

## Retrieval Flow

Retrievers return `RetrievalResult` objects. The store deduplicates them by `record_id`, keeps the best-scoring result, then loads the full records.

```mermaid
flowchart LR
    A["MemorySearch"] --> B["MemoryRetriever"]
    B --> C["RetrievalResult list"]
    C --> D["Deduplicate by record_id"]
    D --> E["MemoryStorage"]
    E --> F["LongTermRecord list"]
```

This keeps retrieval and storage independent:

- the retriever can use keyword search, vector search, graph traversal, or time filters
- the storage layer still owns the real records
- the rest of the application only receives typed long-term records

## Retrieval Result

`RetrievalResult` is the output contract for retrievers:

```python
RetrievalResult(
    record_id="...",
    source="lexical",
    score=0.82,
    relevance_score=0.82,
    recency_score=None,
    importance_score=None,
    reason="matched query tokens against record text",
)
```

`source` is the retrieval method, not the class name. Use stable labels such as:

```text
lexical
semantic
episodic
procedural
hybrid
```

`score` is the retriever's composite ranking score. It is useful for ordering results from a retriever, but it is not a universal confidence score across every retrieval method.

The optional component scores prepare the system for memory-native ranking:

```text
relevance_score  — how well the record matches the query
recency_score    — how fresh or temporally relevant the record is
importance_score — how important the record is to keep or recall
```

`reason` is for debugging and observability. Retrieval logic should not depend on it.

When multiple retrievers find the same record, hybrid retrieval combines their ranks with Reciprocal Rank Fusion.

## Hybrid Fusion

`HybridMemoryRetriever` uses Reciprocal Rank Fusion.

Each child retriever still scores and ranks its own results. Hybrid fusion then combines those ranked lists by position instead of comparing raw scores directly.

```text
RRF score = sum(1 / (rank_constant + rank))
```

The default `rank_constant` is `60`.

This matters because raw scores from different retrievers are not naturally comparable:

```text
lexical score   — token overlap, usually 0 to 1
semantic score  — vector similarity
episodic score  — relevance plus recency
```

RRF lets agreement across retrievers matter. A record that appears reasonably high in several retrievers can outrank a record that appears first in only one retriever.

Example:

```text
Lexical:
1. A
2. B

Semantic:
1. B
2. C

Hybrid RRF:
1. B
2. A
3. C
```

The individual retriever scores remain on each retriever result for debugging. The hybrid result's `score` is the RRF score.

## Current Retrievers

| Retriever | Purpose |
| --- | --- |
| `LexicalMemoryRetriever` | Baseline keyword/text overlap search |
| `SemanticMemoryRetriever` | Embedding-based vector similarity search |
| `EpisodicMemoryRetriever` | Event retrieval, ranked by match and recency |
| `ProceduralMemoryRetriever` | Workflow retrieval by key and steps |
| `HybridMemoryRetriever` | Combines multiple retrievers using Reciprocal Rank Fusion |

## Type-Specific Retrieval

Each long-term memory type should be retrieved according to how it is used.

| Memory type | Retrieval strategy |
| --- | --- |
| `semantic` | vector similarity, lexical fallback, metadata filters |
| `entity` | entity lookup, vector search, graph traversal later |
| `episodic` | recency, participant/entity, event type, time window |
| `procedural` | key lookup, workflow name, task type |
| `preference` | user/profile filters, semantic search |
| `decision` | project/session filters, key lookup, semantic search |

## Metadata Filtering

Metadata filters are applied before scoring.

Supported now:

```python
MetadataFilter(
    equals={"region": "KE"},
    contains_all_tags={"cards", "alerts"},
    created_after=some_datetime,
    created_before=some_datetime,
    occurred_after=some_datetime,
    occurred_before=some_datetime,
)
```

Filtering before scoring matters because it prevents irrelevant memories from winning just because their text looks similar.

Example:

```text
Query: "card alerts"

Memory A:
  region = KE
  content = "Card alerts can be sent by SMS."

Memory B:
  region = UG
  content = "Card alerts can be sent by SMS."

If the active customer is in KE, Memory B should not compete.
```

`created_after` and `created_before` filter by when the memory record was stored.

`occurred_after` and `occurred_before` filter episodic memories by when the event actually happened. This distinction matters when an event is written to memory later than the real-world event time.

Retrieval also applies record lifecycle filtering before scoring:

```text
expires_at in the past      → do not retrieve
invalidated_at is not null  → do not retrieve
```

This keeps stale or superseded memory out of the model context while still allowing the storage layer to keep the record for auditability, debugging, or historical analysis.

## Why Not Only Keywords?

Keyword search is useful, but it is not enough for semantic memory.

Example:

```text
Query:
"Can this customer receive card alerts by SMS?"

Saved memory:
"Customer prefers text message notifications for fraud and card activity."
```

A keyword search may miss the match because `SMS` and `text message notifications` are different words. A semantic retriever can match the meaning.

That is why the architecture separates:

```text
Lexical retrieval  — exact-ish words
Semantic retrieval — meaning
Metadata filters   — scope and governance
Hybrid retrieval   — combine strengths
```

## Current Status

Implemented:

- `MemorySearch`
- `MetadataFilter`
- `RetrievalResult`
- lexical retrieval
- semantic retrieval interface with injected embedder
- episodic retrieval
- procedural retrieval
- hybrid retrieval with Reciprocal Rank Fusion
- namespace, memory type, metadata, tag, created-time, occurred-time, and lifecycle filters

Still needed:

- production embedding provider
- vector index or vector database
- reranking
- graph/entity traversal
- retrieval tests
