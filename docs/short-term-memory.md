# Short-Term Memory

Short-term memory is the thread-scoped conversation state an agent needs while continuing a conversation.

In this repo, short-term memory is deliberately narrow:

```text
persist the ordered conversation timeline
prepare a smaller model context before invocation
keep storage separate from prompt construction
```

It is not long-term memory. It does not decide what facts should be remembered across projects, users, or future sessions. Long-term memory is covered in [long-term-memory.md](long-term-memory.md).

## Core Ideas

Short-term memory answers:

```text
What happened in this thread?
```

The implementation has three main parts:

```text
ConversationState   -> stored timeline shape
ConversationMemory  -> application-facing API
ConversationStorage -> persistence contract
```

The important separation:

```text
state      = what memory looks like
memory API = how application code writes/reads it
storage   = where it is persisted
processors = what context is sent to the model
```

## Data Model

The stored timeline is made of `ConversationItem` objects.

Current item types:

```text
Message
SummaryItem
ToolCall
ToolResult
RetrievalItem
```

The most common item is `Message`.

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

Why these fields matter:

```text
id          -> stable reference for tracing and summaries
created_at  -> ordering and observability
run_id      -> connects a message to an execution/run
model_name  -> records which model produced an answer
usage       -> token/cost accounting
metadata    -> provider or app-specific details
```

`ConversationState` stores ordered items:

```python
ConversationState(
    thread_id="thread-rag",
    items=[
        Message(role="user", content="Explain reranking."),
        Message(role="assistant", content="Reranking sorts retrieved documents."),
    ],
)
```

It also exposes `messages` as a filtered view over `items`.

## Conversation API

`ConversationMemory` is the public API.

```python
memory.add_message(
    thread_id="thread-rag",
    role="user",
    content="Explain reranking.",
)

messages = memory.get_messages("thread-rag")
items = memory.get_items("thread-rag")
```

The API creates memory items and delegates persistence to the configured storage backend.

## Persistence Pattern

Normal conversation writes are append-first:

```text
user message received
append user message
model produces response
append assistant message
```

This is better than rewriting the whole conversation on every turn.

The storage contract supports:

```text
get
create_thread
append_message
append_item
replace_items
replace_messages
delete
```

`replace_*` methods exist for explicit rewrites, but ordinary chat should append.

## Storage Backends

Current backends:

```text
MemoryStorage
JsonStorage
MarkdownStorage
SQLiteStorage
CachedConversationStorage
```

Tradeoffs:

| Backend | Good For | Limitation |
| --- | --- | --- |
| `MemoryStorage` | tests, examples, runtime cache | lost on process restart |
| `JsonStorage` | simple local persistence | weak for concurrency |
| `MarkdownStorage` | human/LLM-readable traces | weaker structured querying |
| `SQLiteStorage` | local durable structured storage | not distributed |
| `CachedConversationStorage` | fast reads with durable primary storage | cache invalidation needs care |

The storage API keeps `ConversationMemory` stable while persistence changes.

## Context Processing

Stored conversation history is not the same thing as model context.

The storage layer can keep the full timeline, while processors decide what subset should be sent to the model.

Current processors:

```text
FilterByRoleProcessor
KeepWithinTokenBudgetProcessor
SummarizeOldMessagesProcessor
ProcessorPipeline
```

## Strategy 1: Role Filtering

`FilterByRoleProcessor` keeps only allowed message roles.

```python
processor = FilterByRoleProcessor(
    allowed_roles={"user", "assistant"},
)
```

Useful when tool outputs, system messages, or internal messages should not be sent to the model for a specific call.

Pros:

```text
simple
predictable
useful for privacy or role-specific context
```

Cons:

```text
can remove important tool context
must be careful with assistant/tool call pairing
```

Future improvements:

```text
role filtering should understand tool call groups
role filtering could be policy-driven per model/provider
```

## Strategy 2: Token-Budget Trimming

`KeepWithinTokenBudgetProcessor` trims by token budget, not message count.

This matters because one message can be tiny:

```text
yes
```

or huge:

```text
Here is a 2,000-line traceback...
```

The processor uses an injected `TokenCounter` so production code can use a model-specific tokenizer.

```python
class TokenCounter(Protocol):
    def count_message(self, message: Message) -> int:
        ...
```

Example:

```python
class WhitespaceTokenCounter:
    def count_message(self, message: Message) -> int:
        return len(message.content.split()) + 1


processor = KeepWithinTokenBudgetProcessor(
    max_tokens=8000,
    token_counter=model_token_counter,
)
```

How it works:

```text
preserve leading system messages when configured
walk backward from newest messages
keep adding message groups while the budget allows
return selected messages in original order
```

It also groups assistant messages with following tool result messages when the assistant message has tool calls. That avoids sending broken tool-call history to providers.

Pros:

```text
closer to production reality than max message count
model tokenizer can be injected
preserves newest context
protects system messages
keeps assistant/tool result groups together
```

Cons:

```text
depends on a correct token counter
can still drop older important facts
does not summarize what it drops
```

Future improvements:

```text
use provider-specific token counters
reserve output tokens explicitly
reserve tokens for retrieved documents and long-term memories
add telemetry showing used/remaining context budget
support multimodal token accounting
```

## Strategy 3: Tool Interaction Compaction

`CompactToolInteractionsProcessor` compacts older assistant/tool-result groups before sending context to the model.

It does not delete the raw stored messages. It only changes the model-facing context.

```python
processor = CompactToolInteractionsProcessor(
    keep_recent_tool_interactions=2,
    max_tool_result_chars=500,
)

model_context = processor.process(
    messages=memory.get_messages("thread-1"),
    context=ProcessingContext(),
)
```

Before compaction:

```text
assistant -> called get_transactions
tool      -> returned a large transaction payload
assistant -> explained why the card was declined
```

After compaction for older tool interactions:

```text
system -> compacted older tool interaction summary
assistant -> explained why the card was declined
```

The processor keeps recent tool interactions raw because the model may still need exact tool-call structure for the current turn. Older tool calls and tool results are usually expensive context, especially when tools return large JSON payloads, search results, logs, or transaction lists.

Pros:

```text
reduces old tool-result noise
keeps recent tool interactions raw
preserves raw messages in storage
tracks compacted message ids in metadata
works without an extra model call
```

Cons:

```text
deterministic compaction is less rich than LLM summarization
truncated tool results can lose details
tool-specific compaction policies may be needed later
```

Future improvements:

```text
tool-specific compactors
LLM-based tool result summaries
structured compaction records
redaction rules for sensitive tool outputs
context telemetry for compacted tool tokens
```

## Strategy 4: Summary Compression

`SummarizeOldMessagesProcessor` summarizes older messages and keeps recent messages raw.

```python
processor = SummarizeOldMessagesProcessor(
    model=summary_model,
    trigger_message_count=8,
    keep_recent_messages=4,
)

model_context = processor.process(
    messages=memory.get_messages("thread-1"),
    context=ProcessingContext(),
)
```

The output shape:

```text
system summary message
recent raw messages
```

The processor does not delete stored messages. It only prepares model context.

The summary prompt lives in:

```text
src/agent_memory/prompts/conversation_summary.yaml
```

Pros:

```text
keeps useful older context in compressed form
reduces model input size
preserves raw messages in storage
prompt is versioned outside code
```

Cons:

```text
summary quality depends on the summarizer model
summaries can lose details
summaries can introduce mistakes if the model is careless
extra model call adds latency and cost
```

Future improvements:

```text
structured summary output
summary quality checks
incremental rolling summaries
domain-specific summary prompts
summary evaluation against raw history
```

## Strategy 5: Persisted Summaries

Summaries can be saved back into the timeline as `SummaryItem`.

```python
memory.add_summary(
    thread_id="thread-1",
    content="The user is building an agent memory system.",
    covered_item_ids=[
        "message-id-1",
        "message-id-2",
    ],
)
```

This does not make the summary the source of truth.

The source of truth remains the raw conversation messages.

Persisted summaries are derived context:

```text
raw messages  -> audit, replay, debugging, evaluation
SummaryItem   -> cheaper context, faster continuation
```

Pros:

```text
summary is traceable through covered_item_ids
raw messages remain available
can avoid regenerating the same summary repeatedly
fits the conversation timeline model
```

Cons:

```text
requires policy for when to create summaries
requires policy for which summary to use later
can create redundant summaries without deduplication
```

Future improvements:

```text
summary reuse policy
summary invalidation when old messages change
compaction telemetry
summary lineage tracking
```

## Strategy 6: Processor Pipeline

`ProcessorPipeline` chains processors.

```python
processor = ProcessorPipeline(
    processors=[
        CompactToolInteractionsProcessor(
            keep_recent_tool_interactions=2,
        ),
        SummarizeOldMessagesProcessor(
            model=summary_model,
            trigger_message_count=20,
            keep_recent_messages=8,
        ),
        KeepWithinTokenBudgetProcessor(
            max_tokens=8000,
            token_counter=model_token_counter,
        ),
    ]
)
```

Pros:

```text
processors stay small
processing order is explicit
easy to compose filtering, trimming, and summarization
```

Cons:

```text
processor order matters
bad ordering can drop context before summarization sees it
pipeline needs stronger validation as it grows
```

Future improvements:

```text
named processing profiles
pipeline validation
before/after processor telemetry
provider-specific processing presets
```

## LLM Boundary

Stored conversation messages are not the same as provider/model messages.

Stored messages include:

```text
id
created_at
run_id
model_name
usage
metadata
tool_calls
```

Model-facing messages use:

```text
SystemMessage
HumanMessage
AIMessage
ToolMessage
ToolCall
```

The adapter boundary is:

```text
src/agent_memory/llm/adapters.py
```

This keeps provider concerns out of stored conversation state.

## What To Improve Next

The important next improvements are:

```text
real provider-specific token counters
context-window telemetry
summary reuse policy
tool-call aware role filtering
structured summarization
long-term memory extraction from short-term history
```

Short-term memory should remain focused on thread state and model-context preparation. Facts, preferences, decisions, and reusable knowledge should move into long-term memory.
