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
metadata    — source, confidence, timestamps, and any other context
```

Typed records then add their own fields:

| Record | Extra structure |
| --- | --- |
| `KnowledgeMemory` | `content`, `source` |
| `EntityMemory` | `name`, `description` |
| `EventMemory` | `description`, `occurred_at` |
| `WorkflowMemory` | `steps: list[str]` |

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
search(namespace, query, memory_type?)    — find records by meaning, keyword, or time
delete(namespace, key)                    — remove a record and its search data
```

These operations do not change when the retrieval strategy improves. Switching from keyword to vector retrieval changes the internals, not how the rest of the program uses long-term memory.

The names in code are:

```
LongTermRecord  — shared base for saved long-term memory records
MemoryStorage   — saves and loads records
InMemoryStorage — temporary storage for local runs and tests
MemoryRetriever — searches records
MemoryStore     — coordinates storage and retrievers
```

The folder structure separates the core memory store from type-specific memory concepts:

```
long_term/
  item.py          — LongTermRecord and MemoryType
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

- `LongTermRecord` shared base with namespace, key, memory type, created time, and metadata
- Typed long-term records for knowledge, entities, events, and workflows
- `MemoryStorage` protocol
- `MemoryRetriever` protocol
- `MemoryStore` main operations — put, get, search, delete
- Retrieval modules for lexical, semantic, episodic, procedural, and hybrid search

In progress:

- SQLite store implementation
- Memory extraction from conversation messages
