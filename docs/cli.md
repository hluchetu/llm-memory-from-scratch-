# CLI Architecture

This document explains the command-line interface architecture for this repository.

The CLI should be small, inspectable, and built around the agent runtime we own:

```text
Agent
AgentSession
AgentRunner
ConversationMemory
MemoryStore
MemoryContextBuilder
MemoryExtractor
```

The CLI is not the agent runtime. It is the terminal entry point into the runtime.

## Design Goals

The CLI should make the memory system usable and inspectable from the terminal.

It should support:

```text
chatting with an agent
continuing a thread
viewing conversation history
clearing a thread
searching long-term memory
inspecting saved memory
running domain-specific agents later
```

It should not hide the memory architecture.

When a command runs, the user should be able to understand:

```text
which thread is active
which namespace is active
which model is used
which long-term memories were retrieved
which long-term memories were extracted
where data is persisted
```

## Command Shape

The initial command surface should stay simple:

```text
agent-memory chat THREAD_ID
agent-memory show-thread THREAD_ID
agent-memory clear-thread THREAD_ID
agent-memory search-memory NAMESPACE QUERY
agent-memory show-memory NAMESPACE
```

Later, domain-specific commands can be added:

```text
agent-memory job-search USER_ID
agent-memory extract-memory THREAD_ID NAMESPACE
agent-memory inspect-run RUN_ID
```

The rule:

```text
Core commands expose the memory system.
Domain commands use the memory system.
```

## Chat Command

`chat` should be the first real runtime command.

The current target flow:

```text
agent-memory chat THREAD_ID --namespace user/hayat
```

Runtime flow:

```text
create Agent
create AgentSession(thread_id, namespace)
create AgentRunner
loop:
  read user input
  runner.run(agent, session, user_input)
  print result.output
```

The chat command should use `AgentRunner`, not call the model directly.

This keeps CLI behavior aligned with the architecture:

```text
CLI
  -> AgentRunner
  -> ConversationMemory
  -> MemoryContextBuilder
  -> ChatModel
  -> MemoryExtractor
  -> MemoryStore
```

## Thread Commands

Thread commands operate on short-term conversation memory.

```text
show-thread THREAD_ID
clear-thread THREAD_ID
```

`show-thread` should show the stored conversation timeline:

```text
message
summary
tool call later
tool result later
retrieval item later
```

This helps verify that conversation memory is persisted correctly.

`clear-thread` should delete only the thread.

It should not delete long-term memory unless a separate memory command explicitly does that.

## Memory Commands

Long-term memory needs its own inspection commands.

Suggested commands:

```text
search-memory NAMESPACE QUERY
show-memory NAMESPACE
```

`search-memory` should run the same retrieval path used by the agent:

```text
query
  -> MemoryStore.search(...)
  -> typed LongTermRecord list
  -> terminal output
```

`show-memory` should list saved records in a namespace when storage supports it. If the current storage backend does not support namespace listing yet, the command should say so clearly.

The CLI should make memory visible, not mysterious.

## Namespace Format

Namespaces should be passed as a slash-separated string:

```text
user/hayat
bank/customer-123
project/agent-memory-from-scratch
```

The CLI converts that into:

```python
("user", "hayat")
("bank", "customer-123")
("project", "agent-memory-from-scratch")
```

This keeps terminal usage simple while preserving the tuple-based internal model.

## Session Identity

The CLI should make the difference between thread and namespace clear.

```text
thread_id  -> the current conversation
namespace  -> the long-term memory scope
```

Example:

```text
thread_id:  job-search-chat-1
namespace:  user/hayat
```

The same namespace can be reused across multiple threads:

```text
job-search-chat-1
job-search-chat-2
interview-prep-chat
```

All can share:

```text
namespace: user/hayat
```

## Output Style

The CLI should prioritize useful output over verbose logs.

During chat:

```text
you> I prefer remote AI engineering roles
assistant> Got it. I will prioritize remote AI engineering roles.
```

Optional inspection after a run:

```text
run_id: ...
memory_used: 3 records
memory_extracted: 1 record
duration_ms: 842
```

The default chat loop should stay readable. Detailed run inspection can become a separate command later.

## Configuration

The CLI should read configuration from settings:

```text
model provider
model name
API key
conversation database path
long-term database path
semantic retrieval enabled
embedding model
vector store path
```

Command flags should override settings only when useful.

Examples:

```text
--database-path
--namespace
--model
--no-memory
```

Do not add many flags before the base loop works.

## Current Implementation

The chat command uses `AgentRunner` directly:

```text
runner.run(agent, session, user_input)
```

This wires the full memory loop — injection before the model call, extraction after the response — into every turn from the terminal.

The next CLI commands to add:

```text
search-memory
show-memory
```

## Design Principle

The CLI should expose the architecture without becoming the architecture.

```text
AgentRunner owns the turn.
ConversationMemory owns the thread.
MemoryStore owns durable memory.
The CLI wires them together for humans.
```
