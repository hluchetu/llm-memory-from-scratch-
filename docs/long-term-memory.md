# Long-Term Memory

Long-term memory stores what should persist beyond a single conversation — facts, preferences, decisions, and events that should be available in future sessions and across users or projects.

The core principle:

> The memory record is the source of truth. Retrievers make records searchable.

Vector embeddings, keyword indexes, graph edges, and timestamps are retrieval structures. They help the system find memory. They are not the memory itself.

## The Memory Record

Every long-term memory entry is a `MemoryRecord` — a typed, namespaced, immutable record with a key and a value.

```
namespace   — where this memory belongs: ("users", "user-123") or ("projects", "my-project")
key         — identifier within the namespace: "preference:output-format"
value       — the memory content: "User prefers concise bullet-point summaries."
memory_type — what kind of memory this is (see below)
metadata    — source, confidence, timestamps, and any other context
```

## Memory Types

Memory type describes what a record represents, not how it is stored. All records share the same shape — `memory_type` drives retrieval strategy and how the record is used in context.

| Type | What it holds | Example |
| --- | --- | --- |
| `semantic` | Facts about the world | "The Humphrey Enterprise contract renews annually." |
| `episodic` | Events that happened | "User rescheduled the Friday event on 2026-06-19." |
| `procedural` | How to do something | "Summarize old messages before trimming by token budget." |
| `preference` | What the user wants | "User prefers metric units and morning reminders." |
| `decision` | What was agreed | "Storage and context are kept as separate layers." |

## Retrieval

Records are found through retrievers. A retriever returns record IDs — the store fetches the full records. This keeps retrieval and storage independent.

```
keyword retriever  → record ids → store → MemoryRecord list
vector retriever   → record ids → store → MemoryRecord list
time retriever     → record ids → store → MemoryRecord list
graph retriever    → record ids → store → MemoryRecord list
```

Different memory types are typically retrieved differently:

- **Semantic and preference** — vector search by relevance to the current query
- **Episodic** — time-bounded search or entity filter
- **Procedural and decision** — direct key lookup, or keyword search when the key is not known

## Public API

The long-term memory layer exposes four operations:

```
put(record)                               — store a record and index it
get(namespace, key)                       — fetch a specific record by key
search(namespace, query, memory_type?)    — find records by meaning or keyword
delete(namespace, key)                    — remove a record and its index entries
```

The API does not change when the retrieval strategy improves. Switching from keyword to vector retrieval is an implementation swap, not an API change.

## Memory Extraction

Long-term records are not written manually — they are extracted from conversations. An extractor reads conversation messages and produces a list of `MemoryRecord` entries to commit.

```
conversation messages → extractor → MemoryRecord list → memory.put(...)
```

Extraction is separate from storage and indexing. The extractor does not know or care what sits behind `memory.put`.

## Relationship to Short-Term Memory

Short-term memory is scoped to a thread. Long-term memory is scoped to a namespace.

At the start of a session, relevant long-term records are retrieved and injected into the system prompt. During or at the end of the session, the agent extracts and commits what should persist. What was said in a conversation becomes what is known across all future conversations.

```
conversation thread → extractor → long-term store
                                       ↓
                              future session context
```

## Current Status

Implemented:

- `MemoryRecord` model with namespace, key, value, memory type, and metadata
- `LongTermMemoryStore` protocol
- `MemoryRetriever` protocol
- `LongTermMemory` public API — put, get, search, delete

In progress:

- SQLite store implementation
- Keyword retriever
- Vector retriever with pluggable embeddings
- Memory extraction from conversation messages
