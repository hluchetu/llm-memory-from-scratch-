# agent-memory-from-scratch

Memory layer for AI agents, built from first principles.

Agent memory is a data flow: what enters the agent, what it retains, what it surfaces, and when. This library builds that flow layer by layer — conversation ledger, context projection, long-term storage, retrieval, extraction, and injection — without prescribing a specific agent SDK or runtime.

Use it with Strands, LangGraph, or any other agent framework.

An article covering the thinking behind this project is at [hluchetu.dev](https://hluchetu.dev).

## Installation

```bash
pip install -e /path/to/agent-memory-from-scratch
```

Set your LLM credentials for memory extraction in `.env`:

```bash
cp .env.example .env
```

## Usage

Every turn runs the same two operations — inject before the model call, extract after.

**Injection — retrieve relevant long-term memories and format them as context:**

```python
from agent_memory.context import LongTermMemoryContextBuilder
from agent_memory.context import MemoryContextRequest

context = context_builder.build(MemoryContextRequest(
    namespace=("user", "alice"),
    query=user_input,
))
# pass context.content as a system message to your agent SDK
```

**Extraction — read new conversation items and persist typed records:**

```python
from agent_memory.extraction import LLMMemoryExtractor
from agent_memory.extraction import MemoryExtractionRequest

result = extractor.extract(MemoryExtractionRequest(
    namespace=("user", "alice"),
    conversation=conversation,
    since_item_id=last_item_id,
))
for record in result.records:
    memory_store.put(record)
```

**Conversation ledger — track what happened in a session:**

```python
from agent_memory.short_term.conversation.memory import ConversationMemory
from agent_memory.storage.sqlite import SQLiteStorage

memory = ConversationMemory(storage=SQLiteStorage(path="threads.db"))
memory.add_message(thread_id="thread-1", role="user", content="Hello")
messages = memory.get_messages("thread-1")
```

**Long-term store — persist and search typed records:**

```python
from agent_memory.long_term.store import MemoryStore
from agent_memory.long_term.semantic import KnowledgeMemory

store.put(KnowledgeMemory(
    namespace=("user", "alice"),
    key="timezone",
    content="User is based in Nairobi, EAT (UTC+3)",
))

records = store.search(
    namespace=("user", "alice"),
    query="What timezone is the user in?",
)
```

## What Is Built

- Typed, immutable conversation events — messages, tool calls, tool results, summaries
- Thread-scoped conversation memory with pluggable storage
- Context trimming by token budget, preserving system messages and tool interaction groups
- Tool interaction compaction — collapses old tool calls into a single summary line
- LLM-based summarization of old messages
- Storage backends: in-memory, SQLite, JSON, Markdown, cached composition
- Provider-neutral LLM message boundary — internal messages stay separate from model messages
- Long-term typed records with namespace, key, metadata, and pluggable retrieval
- Semantic retrieval with Sentence Transformers and Chroma
- Hybrid long-term retrieval with Reciprocal Rank Fusion
- LLM memory extractor — reads conversation threads and produces typed long-term records
- Memory context builder — retrieves relevant long-term records and formats them for model context

## What Is Planned

- Graph retrieval strategies
- Profile memory — durable user and project facts extracted and maintained across sessions
- Knowledge base ingestion from files and folders
- Provider integrations — Mem0, Zep, LangMem
- Context window telemetry and budget reporting
- Multi-agent shared memory

## Architecture

The memory flow is framework-agnostic. Every turn:

```
user input
  → appended to conversation ledger
  → long-term store queried (injection)
  → retrieved records formatted as system message
  → your agent SDK calls the model
  → response appended to ledger
  → LLM extractor runs on new conversation items
  → typed long-term records persisted to store
```

Injection happens before the model call. Extraction happens after. The ledger is the source of truth for both.

```
src/agent_memory/
  short_term/conversation/   # conversation ledger, storage, context processors
  storage/                   # persistence backends (in-memory, SQLite, JSON, Markdown)
  long_term/                 # typed records — episodic, semantic, entity, procedural
  retrieval/                 # lexical, semantic, episodic, procedural, hybrid RRF
  extraction/                # LLM extractor — conversation → typed long-term records
  context/                   # context builder — retrieval → formatted system message
  llm/                       # provider-neutral model boundary
  prompts/                   # YAML prompt templates
  ingestion/                 # source ingestion (in progress)
  integrations/              # external providers (in progress)
```

## Docs

- [Agent Memory Architecture](docs/agent-memory-architecture.md) — architecture choices, tradeoffs, and provider approaches
- [Short-Term Memory](docs/short-term-memory.md) — conversation state, storage, context trimming, summarization
- [Long-Term Memory](docs/long-term-memory.md) — memory items, retrieval strategies, memory types
- [Memory Retrieval](docs/retrieval.md) — lexical, semantic, episodic, procedural, and hybrid retrieval
- [Roadmap](docs/roadmap.md) — what is built, what is in progress, what is planned
