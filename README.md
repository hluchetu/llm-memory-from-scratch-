# agent-memory-from-scratch

Memory architecture for AI agents, built from first principles.

This repo builds agent memory layer by layer — conversation threads, context trimming, summarization, persistent storage, and long-term memory — without reaching for a managed provider until the architecture is clear. The goal is to understand what memory needs to do before deciding what should do it.

An article covering the thinking behind this project is at [hluchetu.dev](https://hluchetu.dev).

## Quick Start

```bash
cp .env.example .env
```

Set your model credentials in `.env`, then start a conversation:

```bash
PYTHONPATH=src python -m agent_memory chat my-thread
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
- Long-term memory records with namespace, key, typed value, and pluggable retrieval
- CLI with persistent conversation memory across runs

## What Is Planned

- Semantic retrieval with embeddings and vector search
- Keyword, time, and graph retrieval strategies
- Memory extraction from conversations into typed long-term records
- Profile memory for durable user and project facts
- Knowledge base ingestion from files and folders
- Provider integrations — Mem0, Zep, LangMem
- Context window telemetry and budget reporting
- Multi-agent shared memory

## Architecture

```
src/agent_memory/
  context/conversation/   # short-term conversation memory
  storage/                # persistence backends
  long_term/              # long-term memory records and retrieval
  llm/                    # provider-neutral model boundary
  prompts/                # YAML prompt templates
  retrieval/              # retrieval strategies (in progress)
  ingestion/              # source ingestion (in progress)
  integrations/           # external providers (in progress)
  agent/                  # minimal agent using the memory layer (in progress)
```

## Docs

- [Short-Term Memory](docs/short-term-memory.md) — conversation state, storage, context trimming, summarization
- [Long-Term Memory](docs/long-term-memory.md) — memory records, retrieval strategies, memory types
