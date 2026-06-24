# Long-Term Memory

Long-term memory stores what should persist beyond a single conversation — facts, preferences, decisions, and events that should be available in future sessions and across users or projects.

The core principle:

> The memory record is the source of truth. Retrievers make records searchable.

Vector embeddings, keyword indexes, graph edges, and timestamps are retrieval structures. They help the system find memory. They are not the memory itself.

## The Memory Record

Every long-term memory is a `LongTermRecord`. The base record contains the fields all long-term memories share:

```
namespace   — where this memory belongs: ("users", "user-123") or ("projects", "my-project")
key         — identifier within the namespace: "preference:output-format"
memory_type — what kind of memory this is (see below)
created_at  — when the record was created
expires_at  — optional time when the record should stop being recalled
invalidated_at — optional time when the record was superseded or contradicted
metadata    — source, confidence, timestamps, and any other context
```

Typed records then add their own fields:

| Record | Extra structure |
| --- | --- |
| `KnowledgeMemory` | `content`, `source` |
| `EntityMemory` | `name`, `description` |
| `EventMemory` | `description`, `occurred_at` |
| `WorkflowMemory` | `steps: list[str]` |

## Record Lifecycle

Long-term memory needs a lifecycle because facts change.

Two fields control whether a record is still eligible for retrieval:

```text
expires_at      — the record becomes stale after this time
invalidated_at  — the record was explicitly replaced, corrected, or revoked
```

The record can still remain in storage for auditability and debugging, but retrieval excludes it from context once either condition applies.

Example:

```python
from datetime import datetime
from datetime import timezone

from agent_memory.long_term import KnowledgeMemory

memory = KnowledgeMemory(
    namespace=("bank", "customer-123"),
    key="daily-transfer-limit",
    content="The customer's daily transfer limit is KES 150,000.",
    source="core-banking-policy",
    expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
)
```

Use `expires_at` when the system already knows when information becomes stale, such as temporary limits, promotional rules, scheduled policy windows, or expiring consent.

Use `invalidated_at` when a newer record contradicts the old one, such as a changed preference, corrected customer profile, replaced workflow, or revoked procedure.

## Memory Types

Memory type describes what a record represents. It also influences how the record is retrieved and how it is used in context.

| Type | What it holds | Example |
| --- | --- | --- |
| `semantic` | Facts about the world | "The Humphrey Enterprise contract renews annually." |
| `entity` | People, customers, accounts, projects, or other named things | "Customer Amina prefers SMS updates." |
| `episodic` | Events that happened | "User rescheduled the Friday event on 2026-06-19." |
| `procedural` | How to do something | "Summarize old messages before trimming by token budget." |
| `preference` | What the user wants | "User prefers metric units and morning reminders." |
| `decision` | What was agreed | "Storage and context are kept as separate layers." |

## Retrieval

Records are found through retrievers. A retriever returns record IDs — the store fetches the full records. This keeps retrieval and storage independent.

For the detailed retrieval architecture, see [Memory Retrieval](./retrieval.md).

```
keyword retriever  → record ids → store → LongTermRecord list
vector retriever   → record ids → store → LongTermRecord list
time retriever     → record ids → store → LongTermRecord list
graph retriever    → record ids → store → LongTermRecord list
```

Different memory types are typically retrieved differently:

- **Semantic, entity, and preference** — vector search by relevance to the current query, often with metadata filters
- **Episodic** — time-bounded search or entity filter
- **Procedural and decision** — direct key lookup, or keyword search when the key is not known

## Main Operations

`MemoryStore` exposes four operations:

```
put(record)                               — store a record and make it searchable
get(namespace, key)                       — fetch a specific record by key
search(namespace, query, memory_type?, metadata?) — find records by meaning, keyword, or time
delete(namespace, key)                    — remove a record and its search data
```

These operations do not change when the retrieval strategy improves. Switching from keyword to vector retrieval changes the internals, not how the rest of the program uses long-term memory.

The names in code are:

```
LongTermRecord  — shared base for saved long-term memory records
MemoryStorage   — saves and loads records
InMemoryStorage — temporary storage for local runs and tests
MemorySearch    — one search request
MetadataFilter  — exact metadata, tag, and creation-time filters
MemoryRetriever — searches records
MemoryStore     — coordinates storage and retrievers
```

The folder structure separates the core memory store from type-specific memory concepts:

```
long_term/
  item.py          — LongTermRecord and MemoryType
  search.py        — MemorySearch and MetadataFilter
  storage.py       — MemoryStorage protocol
  retriever.py     — MemoryRetriever protocol
  store.py         — MemoryStore
  semantic/        — facts, entities, knowledge
  episodic/        — events that happened
  procedural/      — workflows and rules
```

## Memory Extraction

Long-term records are usually extracted from conversations. An extractor reads conversation messages and produces typed records to save.

```
conversation messages → extractor → LongTermRecord list → memory.put(...)
```

Extraction is separate from storage and indexing. The extractor does not know or care what sits behind `memory.put`.

## Relationship to Short-Term Memory

Short-term memory is scoped to a thread. Long-term memory is scoped to a namespace.

At the start of a session, relevant long-term items are retrieved and injected into the system prompt. During or at the end of the session, the agent extracts and saves what should persist. What was said in a conversation becomes what is known across future conversations.

```
conversation thread → extractor → long-term store
                                       ↓
                              future session context
```

## Current Status

Implemented:

- `LongTermRecord` shared base with namespace, key, memory type, created time, lifecycle fields, and metadata
- Typed long-term records for knowledge, entities, events, and workflows
- `MemoryStorage` protocol
- SQLite storage implementation
- `MemoryRetriever` protocol
- `MemoryStore` main operations — put, get, search, delete
- Retrieval modules for lexical, semantic, episodic, procedural, and hybrid search
- `LLMMemoryExtractor` — reads conversation threads and produces typed long-term records
- `LongTermMemoryContextBuilder` — retrieves relevant records and formats them as a system message
- Full extraction and injection wired into `AgentRunner`
