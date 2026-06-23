# Roadmap

## Phase 1 — Memory Infrastructure ✓

- Typed, immutable conversation events — messages, tool calls, tool results, summaries
- Thread-scoped conversation memory with pluggable storage
- Context trimming by token budget, summarization, and tool interaction compaction
- Storage backends — in-memory, SQLite, JSON, Markdown, cached composition
- Long-term typed records — episodic, semantic, entity, procedural, preference, decision
- Long-term SQLite storage with serialization and upsert
- Lexical, semantic, episodic, and procedural retrievers
- Hybrid retrieval with Reciprocal Rank Fusion and type-based routing
- Sentence Transformer embeddings and ChromaDB vector store
- Scored retrieval results with per-retriever sub-scores
- Factory and settings wiring

## Phase 2 — Memory Loop (current)

- [x] Memory extraction interface — define the request/result contract for extracting long-term records from conversation state
- [x] LLM memory extractor — read conversation threads and produce typed long-term records
- [x] Memory context builder — retrieve relevant records and format them for model context
- [x] Agent runtime primitives — Agent, AgentSession, AgentRunner, and AgentResult
- [x] Session wiring — runner adds memory context, calls the model, stores the response, extracts memory, and saves records
- [ ] CLI integration — use AgentRunner in the chat command

## Phase 3 — Knowledge and Profiles

- [ ] Knowledge base ingestion from files and folders into semantic memory
- [ ] Profile memory — durable user and project facts extracted and maintained across sessions

## Phase 4 — Providers and Integrations

- [ ] Mem0 integration — automated memory extraction and deduplication
- [ ] Zep integration — conversation memory with knowledge graph retrieval
- [ ] LangMem integration — LangChain-native memory layer

## Phase 5 — Observability and Scale

- [ ] Context window telemetry and token budget reporting
- [ ] Retrieval observability — scores, sources, and reasons surfaced per search
- [ ] Multi-agent shared memory via namespace-scoped long-term stores
- [ ] PostgreSQL storage backend for production deployments
- [ ] Redis cache layer for hot conversation state and frequently retrieved memories

## Future Storage Direction

SQLite is the right default for this repository today because it keeps the system easy to run locally, easy to inspect, and suitable for a single-agent or single-node setup. It is also a good reference implementation for the storage contract.

For production, the storage layer should evolve toward PostgreSQL and Redis:

- **PostgreSQL** will become the primary durable store for long-term memory records, conversation timelines, audit metadata, namespaces, lifecycle fields, and future multi-tenant access patterns. It gives us stronger concurrency, migrations, indexing, backup/restore, row-level security, and operational tooling than a local SQLite file.
- **Redis** will sit in front of durable storage as a fast cache for active threads, recent conversation state, compiled context windows, and frequently retrieved memories. It is useful for low-latency reads, short-lived working state, and reducing repeated database or retrieval work.

The intended architecture is:

```text
agent runtime
  ↓
ConversationMemory / MemoryStore
  ↓
Redis cache for hot state and repeated reads
  ↓
PostgreSQL as durable source of truth
  ↓
retrieval indexes: lexical, vector, graph, or hybrid
```

The important design constraint is that application code should continue to depend on the same storage interfaces. Moving from SQLite to PostgreSQL, or adding Redis in front, should change the backend wiring, not the public memory API.
