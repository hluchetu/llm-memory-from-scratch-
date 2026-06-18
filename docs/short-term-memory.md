# Short-Term Memory Architecture

Short-term memory stores the conversation state for one active thread.

It answers one question:

```text
What has happened in this conversation so far?
```

In this project, short-term memory is built around four concepts:

```text
Message
ConversationState
ConversationMemory
ConversationStorage
```

## Thread

A thread is one conversation.

The `thread_id` identifies that conversation.

Example:

```text
thread-rag
thread-memory
thread-support-case-123
```

If the same `thread_id` is used again, the system continues the same conversation.

If a new `thread_id` is used, the system starts a different conversation.

## Message

A `Message` is one item said by the user, assistant, system, or tool.

Defined in:

```text
src/llm_memory/conversation/state.py
```

Fields:

```text
id
role
content
created_at
run_id
model_name
usage
metadata
```

Example:

```python
Message(
    role="assistant",
    content="SQLite is a local database.",
    run_id="run-001",
    model_name="gpt-5.2",
    usage={
        "input_tokens": 30,
        "output_tokens": 12,
    },
    metadata={
        "finish_reason": "stop",
    },
)
```

`run_id` connects a message to the model/application execution that produced it.

`model_name` records which model produced the message.

`usage` records token counts or similar usage data.

`metadata` stores extra structured information.

## ConversationState

`ConversationState` is the current state of one conversation thread.

Defined in:

```text
src/llm_memory/conversation/state.py
```

It contains:

```text
thread_id
messages
```

Example:

```python
ConversationState(
    thread_id="thread-rag",
    messages=[
        Message(role="user", content="Explain reranking."),
        Message(role="assistant", content="Reranking sorts retrieved documents."),
    ],
)
```

`ConversationState` is the data shape.

It does not decide where data is saved.

It does not perform storage operations.

## ConversationMemory

`ConversationMemory` is the public API for short-term memory.

Defined in:

```text
src/llm_memory/conversation/conversation.py
```

It provides methods such as:

```text
add_message
get_messages
replace_messages
clear_thread
```

Example:

```python
memory.add_message(
    thread_id="thread-rag",
    role="user",
    content="Explain reranking.",
)
```

`ConversationMemory` creates `Message` objects and sends them to the storage layer.

It does not know whether the data is stored in memory, JSON, Markdown, SQLite, or another backend.

## ConversationStorage

`ConversationStorage` defines the persistence contract.

Defined in:

```text
src/llm_memory/storage/interface.py
```

Every storage backend implements:

```text
get
create_thread
append_message
replace_messages
delete
```

This allows different storage backends to be swapped without changing `ConversationMemory`.

## Storage Backends

The project currently has these storage implementations:

```text
MemoryStorage
JsonStorage
MarkdownStorage
SQLiteStorage
CachedConversationStorage
```

### MemoryStorage

Defined in:

```text
src/llm_memory/storage/memory.py
```

Stores conversation state in Python memory.

This is fast, but not persistent. When the Python process exits, the data is gone.

Useful for:

```text
temporary runtime state
small examples
tests
local experiments
```

### JsonStorage

Defined in:

```text
src/llm_memory/storage/json.py
```

Stores conversation state in a JSON file.

Useful for:

```text
structured local persistence
inspection
small applications
```

### MarkdownStorage

Defined in:

```text
src/llm_memory/storage/markdown.py
```

Stores conversation state as Markdown files.

Useful when humans or LLMs should be able to read the stored conversation easily.

### SQLiteStorage

Defined in:

```text
src/llm_memory/storage/sqlite.py
```

Stores conversation state in SQLite.

SQLite uses two tables:

```text
conversations
conversation_items
```

`conversations` stores the thread-level record.

`conversation_items` stores ordered items inside the conversation.

Currently, `ConversationMemory` writes message items. The schema also allows future item types:

```text
message
tool_call
tool_result
retrieval
summary
```

### CachedConversationStorage

Defined in:

```text
src/llm_memory/storage/cached.py
```

Combines two storage backends:

```text
cache
primary
```

Example:

```python
storage = CachedConversationStorage(
    cache=MemoryStorage(),
    primary=SQLiteStorage(path=".memory/conversations.db"),
)
```

Read behavior:

```text
1. Try cache
2. If cache has the thread, return it
3. If cache misses, read from primary
4. Store the result in cache
5. Return the result
```

Write behavior:

```text
1. Write to primary
2. Update cache
```

This keeps `MemoryStorage` useful as a fast runtime cache while keeping SQLite as the primary storage backend.

## Persistence Point

Short-term memory is persisted when a meaningful conversation event happens.

For normal chat:

```text
user message arrives
append user message

assistant message is produced
append assistant message
```

In code, the persistence point is:

```python
ConversationMemory.add_message(...)
```

That method creates a `Message` and calls:

```python
self._storage.append_message(...)
```

The normal path is append-first.

The system does not rewrite the whole conversation for every new message.

## Replace Messages

`replace_messages` exists for intentional changes to a conversation.

Examples:

```text
trimming old messages
compacting history
replacing raw messages with summary + recent messages
manual correction
```

It should not be the normal path for every chat turn.

## Architecture

Direct storage:

```text
ConversationMemory
  -> SQLiteStorage
```

Cached storage:

```text
ConversationMemory
  -> CachedConversationStorage
       -> MemoryStorage
       -> SQLiteStorage
```

The important boundary:

```text
ConversationMemory manages the API.
ConversationStorage manages persistence.
Message and ConversationState define the data.
```

## Relationship To LangGraph

This project does not implement LangGraph checkpoints.

The current short-term memory system is closer to conversation history storage:

```text
thread_id -> messages
```

LangGraph checkpointers store full graph state.

This project focuses first on storing conversation memory explicitly and append-first.

The concepts still map cleanly:

```text
thread_id
conversation state
messages
storage backend
```

## Current Status

Short-term memory currently supports:

```text
thread-based conversations
append-first message persistence
multiple storage backends
cached storage
message metadata
model/run tracking
message history processors
```

Future additions can build on top of this:

```text
tool call items
tool result items
retrieval items
summary items
windowed reads
summary memory
long-term semantic memory
```
