# agent-memory-from-scratch

Memory architecture for AI agents, built from first principles.

Agent memory is a data flow: what enters the agent, what it retains, what it surfaces, and when. This repo builds that flow layer by layer — conversation ledger, context projection, long-term storage, retrieval, extraction, and injection — without reaching for a managed provider until the architecture is clear. The goal is to understand what moves where before deciding what should move it.

An article covering the thinking behind this project is at [hluchetu.dev](https://hluchetu.dev).

## Quick Start

```bash
cp .env.example .env
```

Set your model credentials in `.env`, then start a conversation:

```bash
PYTHONPATH=src python -m agent_memory chat my-thread
```

Use long-term memory by adding a namespace:

```bash
PYTHONPATH=src python -m agent_memory chat my-thread --namespace user/hayat
```

Inspect or clear a thread:

```bash
PYTHONPATH=src python -m agent_memory show-thread my-thread
PYTHONPATH=src python -m agent_memory clear-thread my-thread
```

Supported providers:

```bash
# DeepSeek
AGENT_MEMORY_MODEL_PROVIDER=deepseek
AGENT_MEMORY_MODEL_NAME=deepseek-chat
AGENT_MEMORY_MODEL_BASE_URL=https://api.deepseek.com
AGENT_MEMORY_MODEL_API_KEY=...

# Anthropic
AGENT_MEMORY_MODEL_PROVIDER=anthropic
AGENT_MEMORY_MODEL_NAME=claude-sonnet-4-5
AGENT_MEMORY_MODEL_API_KEY=...
```

## What Is Built

- Typed, immutable conversation events — messages, tool calls, tool results, summaries
- Thread-scoped conversation memory with pluggable storage
- Context trimming by token budget, preserving system messages and tool interaction groups
- Tool interaction compaction — collapses old tool calls into a single summary line
- LLM-based summarization of old messages
- Persisted summaries as derived timeline items
- Storage backends: in-memory, SQLite, JSON, Markdown, cached composition
- Provider-neutral LLM message boundary — internal messages stay separate from model messages
- Long-term typed records with namespace, key, metadata, and pluggable retrieval
- Semantic retrieval with Sentence Transformers and Chroma
- Hybrid long-term retrieval with Reciprocal Rank Fusion
- LLM memory extractor — reads conversation threads and produces typed long-term records
- Memory context builder — retrieves relevant long-term records and formats them for model context
- Agent runtime — Agent, AgentSession, AgentRunner, and AgentResult wired end-to-end
- Full memory loop — injection before the model call, extraction after the response
- CLI with persistent conversation memory and long-term memory across runs

## What Is Planned

- Graph retrieval strategies
- Profile memory — durable user and project facts extracted and maintained across sessions
- Knowledge base ingestion from files and folders
- Provider integrations — Mem0, Zep, LangMem
- Context window telemetry and budget reporting
- Multi-agent shared memory

## Architecture

Every turn runs the same flow:

```
user input
  → appended to conversation ledger
  → long-term store queried with user input as the search query
  → retrieved records injected as a system message
  → model called: system prompt + memory context + conversation history
  → response appended to ledger
  → LLM extractor runs on new conversation items
  → typed long-term records persisted to store
```

Injection happens before the model call. Extraction happens after. The ledger is the source of truth for both.

```
src/agent_memory/
  agent/                     # Agent, AgentSession, AgentRunner, AgentResult
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

- [Agent Memory Architecture](docs/agent-memory-architecture.md) — architecture choices, tradeoffs, provider approaches, and why this repo is designed this way
- [Agent Runtime Architecture](docs/agent-architecture.md) — how the agent layer is structured around agent, session, runner, and result
- [CLI Architecture](docs/cli.md) — command design, session identity, memory inspection, and how the CLI uses the agent runtime
- [Short-Term Memory](docs/short-term-memory.md) — conversation state, storage, context trimming, summarization
- [Long-Term Memory](docs/long-term-memory.md) — memory items, retrieval strategies, memory types
- [Memory Retrieval](docs/retrieval.md) — lexical, semantic, episodic, procedural, and hybrid retrieval
- [Roadmap](docs/roadmap.md) — what is built, what is in progress, what is planned
