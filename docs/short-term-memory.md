# Short-Term Memory

Short-term memory is what an agent keeps for the current conversation — what happened in this thread, and what the model should see on the next turn.

It has two responsibilities that are deliberately kept separate:

- **The ledger** — the full ordered record of everything that happened
- **The projection** — the subset of that record the model actually receives

The ledger never shrinks. The projection is trimmed, filtered, and compressed on every turn.

## The Ledger

Every event in a conversation is stored as a typed, immutable item. Current item types:

| Type | What it represents |
| --- | --- |
| `Message` | A user, assistant, system, or tool message |
| `ToolCall` | A tool invocation by the assistant |
| `ToolResult` | The result returned by a tool |
| `SummaryItem` | A derived summary of older messages |
| `RetrievalItem` | A document or fact retrieved from external sources |

The conversation thread stores all items in order. A `.messages` property filters to just the `Message` items when that is all that is needed.

## Storage

The ledger is persisted through a storage interface. Any backend that satisfies the interface is a valid implementation:

| Backend | When to use it |
| --- | --- |
| In-memory | Tests and short-lived sessions |
| SQLite | Local development and single-server production |
| JSON | Simple file-based persistence |
| Markdown | Human-readable conversation logs |
| Cached | SQLite or JSON with a fast in-memory read cache |

Conversation writes are append-first. The full thread is only rewritten when messages are explicitly replaced — for example, after summarization.

## The Projection

The stored ledger is not what the model receives. Before each model call, the ledger is passed through a processing pipeline that produces a clean, token-efficient view.

Each step has one job:

**Type filtering** — strips events the model does not need. Internal metadata, retrieval items, and duplicate system messages are removed first.

**Token-budget trimming** — walks backwards from the most recent event, keeping everything that fits within a token budget. System messages are always preserved first. Tool call and tool result pairs are kept together — they are never split.

**Tool interaction compaction** — rather than dropping old tool interactions entirely, collapses them into a single summary line: the tool name, arguments, and outcome. The model knows what happened without receiving the full payload.

**Summarization** — when the conversation exceeds a threshold, the oldest messages are replaced by an LLM-generated summary. Recent messages remain raw. The summary is injected as a system message at the top of the projection.

Steps are composed into a pipeline. Order matters — compaction should run before trimming so the trimmer sees already-compacted tool interactions.

## Persisted Summaries

Summaries can be written back into the ledger as `SummaryItem` records. This means the summary is traceable — it carries the IDs of the messages it covers — and avoids regenerating the same summary on every turn.

The raw messages remain the source of truth. Persisted summaries are derived context, not a replacement.

## Model Message Boundary

Saved conversation items are not the same as messages sent to a model provider. The internal format carries fields like `run_id`, `model_name`, `usage`, and `metadata` that model APIs do not accept.

An adapter layer converts internal items to the provider format before the model call. This keeps provider-specific details out of the saved conversation and makes it straightforward to support multiple providers from the same memory layer.
