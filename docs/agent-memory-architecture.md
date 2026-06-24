# Agent Memory Architecture

This document explains the architecture behind this repository: what agent memory is, which memory architectures are common, why this project is structured the way it is, and when a different architecture would be the better choice.

The goal is not to copy one provider. The goal is to understand the design space well enough to choose the right architecture for the job.

## The Core Distinction

Agent memory has two separate questions:

```text
What is being remembered?
How is it stored, retrieved, updated, and governed?
```

The first question is about **memory type**.

The second question is about **memory architecture**.

Example:

```text
Memory type:
"The customer prefers SMS alerts."

Architecture:
Store it as a typed long-term record, persist it in PostgreSQL, index it in a vector store, and invalidate it if the preference changes.
```

The memory type is the content. The architecture is the system that manages that content.

## What Memory Does For An Agent

Memory gives an agent continuity.

Without memory, every model call starts almost from zero. The agent can only use what is inside the current prompt. That works for short tasks, but it breaks down when the agent needs to maintain user preferences, remember prior decisions, reuse procedures, or reason over events that happened across sessions.

Memory helps an agent answer questions like:

```text
What did this user prefer last time?
What happened earlier in this case?
What rules apply to this workflow?
What did we already decide?
Which facts are still valid?
Which old facts have been replaced?
```

The important point is that memory is not just storage. A database can store information, but memory also needs retrieval, lifecycle management, context selection, and governance.

## Memory Types

Memory types describe what kind of information is being stored.

| Type | Meaning | Example |
| --- | --- | --- |
| Working memory | Current task context | Recent conversation turns, tool results, active user request |
| Semantic memory | Facts, knowledge, rules, and concepts | "Premium accounts have free international transfers." |
| Episodic memory | Events that happened | "Customer reported card fraud on 2026-06-20." |
| Procedural memory | How to do something | "To replace a card: verify identity, block old card, issue new card." |
| Preference memory | User or customer preferences | "Customer prefers SMS instead of email." |
| Decision memory | Agreements or choices that should persist | "Use PostgreSQL as the future source of truth." |

These are not storage engines. They are categories of information. A semantic memory can live in Markdown, PostgreSQL, a vector database, or a graph-backed system depending on the architecture.

## Architecture 1: Working-Only Memory

Working-only memory keeps everything inside the current model context.

```text
conversation messages -> context window -> model
```

Example:

```text
User: I lost my card.
Assistant: I can help you block it.
User: Also send alerts by SMS.
```

The model remembers the SMS preference only because it is still in the current context window.

Pros:

- Very simple
- No database required
- Accurate for recent conversation
- Easy to debug

Cons:

- Memory disappears when the context is gone
- Long conversations become expensive
- No cross-session continuity
- No durable audit trail

Use this for:

- Short chats
- Stateless assistants
- Small demos
- Early prototypes

This repository uses working memory as part of short-term conversation memory, but does not treat it as enough for a complete agent memory system.

## Architecture 2: Checkpointed Conversation Memory

Checkpointed conversation memory saves the current thread state.

```text
thread_id -> conversation state -> checkpointer or database
```

Example:

```text
thread_id = "customer-support-session-123"

messages:
- user: I lost my card
- assistant: I can help block it
- user: Please send alerts by SMS
```

If the process restarts, the application can reload the thread.

Pros:

- Supports multi-turn conversations
- Survives process restarts
- Works well for graph-based agent execution
- Enables interrupt and resume workflows

Cons:

- Conversation history is noisy
- Long histories still need trimming or summarization
- Not every message should become long-term memory
- Saving the thread is not the same as extracting durable knowledge

Use this for:

- Chat applications
- Multi-step agents
- Human-in-the-loop systems
- Workflow agents that need thread continuity

LangGraph uses this pattern heavily. Its memory docs separate short-term thread memory from long-term memory across sessions, and show production checkpointers backed by databases such as Postgres and Redis.

In this repository, the equivalent pieces are:

```text
ConversationState   -> the saved conversation
ConversationMemory  -> the class used to add and read messages
ConversationStorage -> where conversations are saved
processors          -> what context is sent to the model
```

## Architecture 3: Flat Vector Memory

Flat vector memory stores text, embeds it, and retrieves similar text later.

```text
memory text -> embedding -> vector database -> top-k semantic search
```

Example memory:

```text
"Customer prefers SMS alerts for card transactions."
```

Query:

```text
"How should we notify this customer?"
```

Vector search can retrieve the memory because the meaning is similar even if the words do not match exactly.

Pros:

- Good semantic recall
- Simple mental model
- Useful when wording differs between query and memory
- Easy to build with Chroma, pgvector, Pinecone, Weaviate, or similar systems

Cons:

- Weak at exact structured facts unless metadata is used well
- Weak at relationships and multi-hop reasoning
- Weak at temporal reasoning
- Can retrieve stale information without lifecycle fields
- Flat chunks can lose structure

Use this for:

- Knowledge base recall
- Semantic facts
- User preferences
- Documentation search
- Support policy retrieval

In this repository, this maps to:

```text
KnowledgeMemory
  -> SentenceTransformer embedding
  -> Chroma vector store
  -> SemanticMemoryRetriever
```

Flat vector memory is useful, but it should not become the whole memory architecture.

## Architecture 4: Extracted Fact Memory

Extracted fact memory does not store the entire conversation as memory. It extracts durable facts, preferences, events, or decisions from the conversation.

```text
conversation -> LLM extraction -> typed memory records -> storage and retrieval
```

Example conversation:

```text
User: I travel often, so please do not send OTPs by email. SMS is better.
```

Extracted memory:

```python
PreferenceMemory(
    namespace=("bank", "customer-123"),
    key="otp-channel",
    value="Customer prefers SMS for OTP because they travel often.",
)
```

Pros:

- Stores useful memory instead of raw chat noise
- Reduces token cost
- Improves personalization
- Easier to retrieve than entire conversation logs
- Works well across sessions

Cons:

- Extraction can miss important details
- Extraction can create bad memory if the prompt or validation is weak
- Needs deduplication
- Needs update and invalidation logic
- Needs evaluation

Use this for:

- Personalization
- Customer support
- Long-running assistants
- Agents that should improve over time

Mem0 is close to this pattern. Its paper focuses on scalable long-term memory through selective memory formation and retrieval rather than repeatedly sending full conversation history.

This repository implements this pattern. The full per-turn flow is:

```text
user input
  -> conversation ledger
  -> long-term store queried (injection)
  -> retrieved records injected as system message
  -> model called
  -> response stored in ledger
  -> LLM extractor runs on new conversation items
  -> typed LongTermRecord persisted to MemoryStore (extraction)
```

## Architecture 5: Stateful Agent Memory

Stateful agent memory gives the agent explicit memory blocks or state that can persist and sometimes be edited by the agent through tools.

```text
core memory blocks -> model context -> agent can update memory through tools
```

Example:

```text
customer_profile:
"Customer is Amina. Prefers SMS. Usually contacts support from Nairobi."

agent_instructions:
"When handling card fraud, block the card before explaining replacement options."
```

Pros:

- Strong continuity for long-running agents
- Important memory can stay close to the model context
- The agent can actively manage memory
- Useful for agents that evolve over time

Cons:

- More complex than passive retrieval
- Memory editing needs guardrails
- Bad writes can pollute future behavior
- Tool permissions and validation matter

Use this for:

- Personal agents
- Coding agents
- Research agents
- Autonomous assistants
- Agents with evolving behavior

Letta, influenced by MemGPT, follows this kind of stateful-agent direction: agent state includes memory, messages, reasoning traces, and tool interactions, with memory made available in context and updated through the system.

This repository does not fully implement this pattern yet. The current design keeps the foundation provider-neutral so a Letta-style layer can be added later without rewriting the memory model.

## Architecture 6: Hybrid Relational And Vector Memory

Hybrid relational and vector memory keeps structured records in a primary database and uses a vector index for semantic recall.

```text
primary database = source of truth
vector index     = semantic retrieval projection
```

Example:

```python
KnowledgeMemory(
    namespace=("bank", "customer-123"),
    key="sms-alert-preference",
    content="Customer prefers SMS alerts for card activity.",
    source="support-conversation",
)
```

The database stores the real record.

The vector store stores:

```text
record_id -> embedding
```

Search flow:

```text
query -> vector search -> record_id -> load full typed record from database
```

Pros:

- Clean source of truth
- Typed records keep structure
- Vector search handles meaning
- Easier to audit than vector-only memory
- Easier to expire or invalidate stale memories
- Practical production path

Cons:

- More moving parts than a single database
- Requires sync between database and vector index
- Needs reindexing and backfill strategy
- Metadata filtering still matters

Use this for:

- Most serious semantic memory systems
- Knowledge memory
- Profile memory
- Preference memory
- Customer support memory

This is the current direction of this repository:

```text
SQLite now
PostgreSQL later
Chroma now
Production vector store later
```

This is the architecture I would defend as the first production-grade step before adding graph complexity.

## Architecture 7: Hybrid Graph And Vector Memory

Hybrid graph and vector memory adds a graph index for relationships and temporal reasoning.

Example graph projection:

```text
Customer Amina
  -> owns
Account 123
  -> has_card
Card 987
  -> reported_fraud_on
2026-06-20
```

This helps answer questions like:

```text
Which customer reported fraud on a card linked to this account last week?
```

That is not just semantic similarity. It requires entity relationships, events, and time.

Pros:

- Strong for relationship reasoning
- Strong for multi-hop questions
- Strong for temporal memory
- Useful for enterprise and domain-heavy systems
- Can model changing facts better than flat chunks

Cons:

- More complex to build and operate
- Entity extraction quality matters
- Graph schema design matters
- Not every memory deserves graph projection

Use this for:

- Banking support agents
- Healthcare agents
- Legal case agents
- CRM agents
- Enterprise assistants
- Multi-hop relationship questions

Zep's Graphiti is an example of this direction. It uses a temporal knowledge graph architecture for dynamic agent memory and combines graph, time, semantic, and text retrieval ideas.

This repository should add graph memory later as a projection layer, not as the only storage layer.

## Architecture 8: Hybrid Graph-Relational Memory

This is the long-term production direction for this repository.

The core idea:

```text
PostgreSQL or document storage = source of truth
Vector index                   = semantic recall
Graph index                    = relationship and temporal reasoning
Redis                          = hot state and cache
```

The primary database stores the typed record:

```python
EventMemory(
    namespace=("bank", "customer-123"),
    key="event:fraud-report:2026-06-20",
    description="Customer reported card fraud through the mobile app.",
    occurred_at=fraud_report_time,
    metadata={"channel": "mobile_app"},
)
```

The graph stores a projection:

```text
(Customer)-[:REPORTED]->(FraudEvent)-[:AFFECTS]->(Card)
```

The vector index stores a semantic projection:

```text
"Customer reported card fraud through the mobile app."
```

The time index uses:

```text
occurred_at = 2026-06-20
```

Pros:

- Best balance for serious systems
- Records stay structured and auditable
- Graph is used only where it helps
- Vector search handles fuzzy meaning
- Relational storage handles lifecycle, governance, migrations, and transactions
- Easier to reason about than graph-only storage

Cons:

- Requires background sync workers
- Requires observability
- Requires reindexing strategy
- More infrastructure than a simple local project

Use this for:

- Regulated domains
- Multi-tenant systems
- Enterprise assistants
- Agents needing auditability plus semantic and relationship retrieval

This is why the roadmap says this repository will migrate toward PostgreSQL and Redis later.

## Why Not Store Everything In A Graph?

A graph database is powerful, but it is not automatically the best primary store for every memory.

Use graph when the query depends on relationships:

```text
Which accounts are connected to the customer who reported this fraud event?
```

Do not force graph when the query is a direct lookup:

```text
What is this customer's preferred notification channel?
```

Do not force graph when the structure is naturally ordered:

```text
Workflow steps:
1. Verify identity
2. Block card
3. Issue replacement
```

For this repository, the better design is:

```text
typed record as source of truth
  -> vector projection for semantic recall
  -> graph projection for relationship reasoning
  -> lexical/time indexes where useful
```

The graph index should be an index, not the memory model itself.

## Provider Approaches

| Provider or framework | Main idea | Architecture style |
| --- | --- | --- |
| LangGraph | Stateful graph execution with checkpointers and stores | Thread memory through state/checkpointing; long-term memory through stores |
| Mem0 | Extract useful memory from interactions | Managed extracted memory, vector search, metadata, graph-enhanced memory |
| Letta / MemGPT | Stateful agents with editable memory | Core memory blocks, archival memory, persisted state and tool interactions |
| Zep / Graphiti | Temporal knowledge graph memory | Entity/relation/event graph with temporal and hybrid retrieval |
| Traditional RAG | Retrieve document chunks | Vector or hybrid search over external documents |
| Enterprise context layer | Governed organizational knowledge | Metadata graph, access control, certified definitions |

## How This Repository Maps To The Design Space

This repository chooses a layered architecture:

```text
Memory type
  -> typed record
  -> storage backend
  -> retrieval projection
  -> context injection
```

Current implementation:

```text
Short-term memory:
  ConversationState
  ConversationMemory
  ConversationStorage
  context processors

Long-term memory:
  LongTermRecord
  KnowledgeMemory
  EntityMemory
  EventMemory
  WorkflowMemory

Extraction:
  LLMMemoryExtractor  — conversation -> typed long-term records
  MemoryExtractionRequest / MemoryExtractionResult

Injection:
  LongTermMemoryContextBuilder  — retrieval -> formatted system message

Agent runtime:
  Agent, AgentSession, AgentRunner, AgentResult

Storage:
  SQLite now
  PostgreSQL later

Retrieval:
  lexical
  semantic
  episodic
  procedural
  hybrid RRF

Lifecycle:
  expires_at
  invalidated_at
```

Planned:

```text
conversation
  -> extractor
  -> typed long-term records
  -> PostgreSQL source of truth
  -> Redis cache for hot state
  -> vector index for semantic recall
  -> graph index for relationship and temporal reasoning
  -> retrieved memory injected into context
```

## Why This Architecture Was Chosen

This project uses typed records because memory should not become an unstructured pile of strings.

An event needs a timestamp. A workflow needs ordered steps. A knowledge fact may need a source. A customer preference needs a namespace and lifecycle. If all of that is flattened into text too early, retrieval becomes easier but memory quality gets worse.

This project uses storage interfaces because the backend should be replaceable.

SQLite is good for local development and inspection. PostgreSQL is better for production durability, concurrency, migrations, indexing, backup, and governance. Redis is useful for hot thread state and repeated reads. The application should not need to change when the backend changes.

This project uses retrieval interfaces because different memory types are found differently.

Semantic facts benefit from vector search. Events benefit from recency and time filters. Workflows benefit from key and lexical search. Future graph retrieval will help with entity relationships and multi-hop questions.

This project uses lifecycle fields because memory changes.

Old facts may expire. New facts may contradict old facts. Long-term memory should not blindly retrieve stale information just because it matched the query.

## When To Use Each Architecture

| Need | Recommended architecture |
| --- | --- |
| Short conversation only | Working-only memory |
| Multi-turn workflow | Checkpointed conversation memory |
| Search over facts or documents | Vector memory |
| Personalization across sessions | Extracted fact memory |
| Agent that edits its own memory | Stateful agent memory |
| Production typed memory | Relational plus vector |
| Relationship or temporal reasoning | Graph plus vector |
| Enterprise governance | Relational/document store plus graph/context layer |

## The Current Flow

Every turn runs this sequence:

```text
user input
  -> short-term conversation ledger
  -> context processors (trim, compact, summarize)
  -> long-term memory retrieval (injection)
  -> model call: system prompt + memory context + conversation history
  -> response stored in ledger
  -> memory extraction: new conversation items -> typed long-term records
  -> records persisted to source-of-truth storage and retrieval indexes
```

Injection happens before the model call. Extraction happens after. The ledger is the source of truth for both. This is what runs today.

The most important principle:

```text
Do not make the database the memory model.

The memory model is the typed record.
The database stores it.
The retrievers index it.
The agent decides when to use it.
```

## References

- [LangGraph memory documentation](https://docs.langchain.com/oss/python/langgraph/add-memory)
- [Letta stateful agents documentation](https://docs.letta.com/guides/core-concepts/stateful-agents)
- [Mem0 platform documentation](https://docs.mem0.ai/platform/overview)
- [Mem0 paper: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413)
- [Zep Graphiti documentation](https://help.getzep.com/graphiti/getting-started/overview)
- [Zep paper: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
- [CoALA paper: Cognitive Architectures for Language Agents](https://arxiv.org/abs/2309.02427)
