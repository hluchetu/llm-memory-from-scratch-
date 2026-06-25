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

## Phase 2 — Memory Loop ✓

- Memory extraction interface — request/result contract
- LLM memory extractor — conversation → typed long-term records
- Memory context builder — retrieval → formatted model context
- Extraction triggers — InvocationTrigger and IntervalTrigger
- Importance scoring — extracted by LLM, stored on record, blended into retrieval scores
- Preference and Decision memory types — dataclasses, extraction, serialization, retrieval, context
- Extraction aware of existing memories — query store, inject context, handle create/update/invalidate
- MemoryManager — coordinates injection, extraction, and recall across multiple stores
- Framework-agnostic design — injection and extraction work with any agent SDK

## Phase 3 — Bug Fixes and Reliability (current)

- [ ] #5 — Semantic retriever loses records across restarts — records must survive process restart
- [ ] #22 — Retry on internal LLM calls — exponential backoff in extractor and summarizer
- [ ] #23 — Retry on storage operations — retry SQLite and Chroma on transient failures

## Phase 4 — Memory Quality

Improvements grounded in research papers (Generative Agents, MemGPT, A-MEM, HippoRAG, CoALA).

- [ ] #4 — Replace token overlap with BM25 in lexical retriever
- [ ] #6 — Memory conflict resolution — detect contradictions, auto-invalidate stale records on write
- [ ] #8 — Normalize scores across retrievers before fusion — episodic score can exceed 1.0
- [ ] #9 — Group context output by memory type instead of flat bullet list
- [ ] #3 — Associative links between records — `related_ids` field, one-hop link following in retrieval
- [ ] #2 — Reflection layer — derive higher-level insights from stored memories via LLM

## Phase 5 — Short-Term Memory

- [ ] #16 — Token-based summarization trigger — replace message count with token threshold
- [ ] #17 — `ConversationState.items_since(item_id)` — replace manual slicing in extractor
- [ ] #18 — Message pinning — protect critical messages from summarization and trimming
- [ ] #19 — Summarizer awareness of existing summaries — avoid re-summarizing old summaries
- [ ] #20 — `ConversationStorage.get_items_since(item_id)` — efficient incremental reads from SQLite

## Phase 6 — SDK Integration

- [ ] #11 — Async support — `AsyncMemoryStore`, `AsyncLLMMemoryExtractor` with same method names
- [ ] #12 — Message format bridge — `messages_to_conversation_state` for provider-format dicts
- [ ] #14 — Pluggable context format — `MemoryFormatter` protocol, BulletList / XML / Grouped formatters
- [ ] #15 — SDK adapter layer — `integrations/` pattern, start with one adapter to validate

## Phase 7 — Evals

- [ ] #24 — Extraction evals — record types, importance scores, deduplication behaviour
- [ ] #24 — Retrieval evals — correct records surface for a query, importance boost validated
- [ ] #24 — Regression suite — fixed scenarios run before and after each change

## Phase 8 — Observability

- [ ] #25 — Structured logging at extraction, retrieval, injection, and storage operations
- [ ] #25 — Timing — how long each operation takes
- [ ] #25 — `MemoryObserver` hook protocol — Langfuse, Phoenix, and custom integrations
- [ ] Context window telemetry and token budget reporting
- [ ] Multi-agent shared memory via namespace-scoped long-term stores

## Phase 9 — Safety and Security

- [ ] #26 — `NamespacePolicy` — enforce read/write access per namespace for multi-tenant deployments
- [ ] #27 — `MemoryValidator` — block credential patterns, anomalous importance scores, behaviour overrides

## Phase 10 — Knowledge and Profiles

- [ ] Knowledge base ingestion from files and folders into semantic memory
- [ ] Profile memory — durable user and project facts extracted and maintained across sessions

## Phase 11 — Providers and Integrations

- [ ] Mem0 integration — plug Mem0 as a MemoryStore implementation
- [ ] Zep integration — plug Zep/Graphiti as a MemoryStore with graph retrieval
- [ ] LangMem integration — LangChain-native adapter

## Phase 12 — Scale

- [ ] PostgreSQL storage backend — production durability, concurrency, row-level security
- [ ] Redis cache layer — hot conversation state and frequently retrieved memories
- [ ] Graph retrieval — entity traversal for multi-hop relationship queries
