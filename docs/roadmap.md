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

- [ ] Memory extraction — read conversation threads, extract typed long-term records using LLM
- [ ] Session injection — retrieve relevant records at session start, inject into system prompt
- [ ] Wire the agent — connect conversation memory, long-term memory, extraction, and injection into a working agent loop

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
