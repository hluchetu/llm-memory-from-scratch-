# Agent Architecture

This document explains the agent runtime architecture — how a turn executes and how the memory layer is wired into it.

The agent layer is built around a clear separation of concerns:

```text
agent definition
runtime session
runner
typed result
explicit dependencies
memory lifecycle
```

The memory layer provides separate building blocks that the runner coordinates:

```text
ConversationMemory             -> saves the current thread
LLMMemoryExtractor             -> extracts long-term records from conversation
MemoryStore                    -> stores and searches long-term records
LongTermMemoryContextBuilder   -> formats retrieved memory for model context
ChatModel                      -> provider-neutral model boundary
```

These pieces are connected through `AgentRunner` without folding them into one large class.

Memory is a capability of the runtime, not the identity of the agent. A banking support agent, research agent, coding agent, or travel agent can all use the same memory architecture without becoming a special "memory agent".

## Architecture We Are Adapting

The agent layer should be split into four concepts:

```text
Agent
AgentSession
AgentRunner
AgentResult
```

This gives each part one job:

```text
Agent         -> what the agent is
AgentSession  -> which conversation and optional memory namespace is active
AgentRunner   -> how one turn executes
AgentResult   -> what happened during the turn
```

## Agent

`Agent` describes stable behavior.

It should hold:

```text
name
instructions
model
tools
output schema
model settings later
```

It should not directly own every storage and memory concern.

Example:

```python
agent = Agent(
    name="bank-support-agent",
    instructions="You are a careful banking support assistant.",
    model=model,
)
```

The agent definition should answer:

```text
Who is this agent?
What instructions guide it?
Which model does it use?
Which tools can it call?
Does it return text or a structured object?
```

It should not answer:

```text
Where is this user's conversation stored?
Which customer namespace is active?
Which memories were retrieved for this turn?
Which new memories were extracted?
```

Those are runtime concerns.

## AgentSession

`AgentSession` identifies the active runtime conversation.

It should hold:

```text
thread_id
namespace when memory is enabled
```

Example:

```python
session = AgentSession(
    thread_id="support-thread-123",
    namespace=("bank", "customer-123"),
)
```

The distinction matters:

```text
thread_id  -> where short-term conversation history is stored
namespace  -> where long-term memories are searched and saved
```

A user can have multiple conversation threads under the same long-term memory namespace.

Example:

```text
namespace = ("bank", "customer-123")

thread_id = "card-support-chat"
thread_id = "loan-application-chat"
thread_id = "mobile-app-support-chat"
```

All three threads can share long-term customer memory while keeping their own short-term conversation state.

## AgentRunner

`AgentRunner` executes one turn.

It coordinates:

```text
ConversationMemory
LongTermMemoryContextBuilder
ChatModel
LLMMemoryExtractor
MemoryStore
tool execution
```

The runner is where the memory loop becomes real.

The runner should receive dependencies explicitly:

```python
runner = AgentRunner(
    conversation_memory=conversation_memory,
    memory_store=memory_store,
    context_builder=context_builder,
    extractor=extractor,
)
```

This keeps the system testable and replaceable:

```text
Use SQLite now, PostgreSQL later.
Use Chroma now, pgvector later.
Use the local extractor now, Mem0 later.
Use a direct runner now, graph execution later.
```

The application code should not need to be rewritten when those internals change.

## AgentResult

`AgentResult` should return the important outputs of the turn.

It should include:

```text
assistant_message
output
raw_output
run_id
started_at
finished_at
duration_ms
memory_context
context_record_ids
extracted_records
tool_calls
tool_results
```

Later it can include:

```text
usage
```

The result should make memory behavior visible.

Instead of only returning a string:

```python
"Yes, you can receive card alerts by SMS."
```

The runner should return enough information to inspect the turn:

```python
AgentResult(
    assistant_message=message,
    memory_context=context,
    context_record_ids=[...],
    extracted_records=[...],
)
```

This matters for debugging and evaluation.

The result should also include lightweight run metadata:

```text
run_id       -> unique identifier for this turn
started_at   -> when the run began
finished_at  -> when the run ended
duration_ms  -> total runtime in milliseconds
```

This gives basic observability without adding a full tracing system.

## Structured Output

Structured output is part of the agent contract.

Some agents return plain text:

```text
"Yes, you can receive card alerts by SMS."
```

Other agents should return a validated object:

```python
class SupportAnswer(BaseModel):
    answer: str
    confidence: float
    requires_human_review: bool
```

The agent should declare the expected output shape:

```python
agent = Agent(
    name="bank-support-agent",
    instructions="You are a careful banking support assistant.",
    model=model,
    output_schema=SupportAnswer,
)
```

The runner handles the runtime work:

```text
call model
  -> parse model output
  -> validate against output schema when one exists
  -> return parsed output in AgentResult
```

The result should keep both:

```text
output      -> validated structured output or final text
raw_output  -> original assistant message content
```

This keeps structured output as a normal agent capability, not a separate agent type.

## The Runtime Flow

One turn looks like this:

```text
1. Receive user input
2. Save user message into ConversationMemory
3. Search long-term memory with LongTermMemoryContextBuilder
4. Build model input:
   - agent instructions
   - long-term memory context
   - recent conversation messages
   - user message
5. Call ChatModel
6. If the model requests tools, execute them through the runner
7. Save tool calls and tool results into ConversationMemory
8. Call ChatModel again when tool results need a final answer
9. Save assistant message into ConversationMemory
10. Run LLMMemoryExtractor on the updated conversation
11. Save extracted LongTermRecord objects into MemoryStore
12. Return AgentResult
```

In code shape:

```python
result = runner.run(
    agent=agent,
    session=session,
    user_input="Can I receive card alerts by SMS?",
)
```

The output should show not only what the model said, but what memory was used:

```python
result.assistant_message
result.context_record_ids
result.extracted_records
```

## Why Not One Big Agent Class?

A single `Agent` class can work for a small demo, but it becomes hard to extend.

If one class owns everything, it eventually mixes:

```text
model configuration
conversation storage
long-term retrieval
prompt building
tool execution
memory extraction
memory persistence
runtime reporting
```

That makes testing harder and architecture harder to explain.

The split we want is:

```text
Agent         -> stable behavior
AgentSession  -> runtime identity
AgentRunner   -> execution order
AgentResult   -> structured output
```

## Relationship To Memory Architecture

The current memory architecture already separates writing memory from reading memory:

```text
extraction = conversation -> durable records
context    = durable records -> model context
```

The agent runner becomes the orchestrator:

```text
ConversationMemory
  -> context builder
  -> model
  -> extractor
  -> MemoryStore
```

This keeps each part replaceable:

```text
ConversationMemory owns thread history.
MemoryStore owns durable records.
ContextBuilder owns model context construction.
Extractor owns memory formation.
Runner owns execution order.
```

## Tools

Tools belong to the agent definition, but tool execution belongs to the runner.

The agent should declare what tools are available:

```python
agent = Agent(
    name="bank-support-agent",
    instructions="You are a careful banking support assistant.",
    model=model,
    tools=[
        block_card,
        check_balance,
        create_support_ticket,
    ],
)
```

The runner should execute the tool lifecycle:

```text
model returns tool call
  -> runner validates the tool call
  -> runner executes the tool
  -> runner stores the tool result in ConversationMemory
  -> runner calls the model again with the tool result
  -> model produces the final assistant response
```

This separation matters because tools are capabilities, while execution is runtime behavior.

The agent says:

```text
These tools are available.
```

The runner decides:

```text
This tool was requested.
This call is valid.
This result should be recorded.
The model should be called again.
```

This also fits the existing conversation model:

```text
Message.tool_calls
ToolCall
ToolResult
```

Tool calls and tool results should become part of the conversation timeline so memory processors, summarizers, and extractors can inspect what happened.

## Extension Points

The agent layer leaves room for:

```text
graph-based execution
human approval
memory evaluation
tool execution in the runner
```

## Design Principle

The runner should orchestrate memory. It should not become the memory system.

```text
The memory model is the typed record.
The database stores it.
The retrievers index it.
The context builder formats it.
The extractor forms it.
The runner coordinates it.
```

That is the architecture this repository has built from scratch.
