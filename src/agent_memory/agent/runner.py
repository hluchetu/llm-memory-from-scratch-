from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from pydantic import ValidationError

from agent_memory.agent.agent import Agent
from agent_memory.agent.result import AgentOutput
from agent_memory.agent.result import AgentResult
from agent_memory.agent.session import AgentSession
from agent_memory.context import MemoryContextBuilder
from agent_memory.context import MemoryContextRequest
from agent_memory.context import MemoryContextResult
from agent_memory.errors import AgentOutputValidationError
from agent_memory.errors import AgentRunError
from agent_memory.extraction import MemoryExtractionRequest
from agent_memory.extraction import MemoryExtractor
from agent_memory.llm.adapters import to_llm_messages
from agent_memory.llm.message import Message as LLMMessage
from agent_memory.llm.message import SystemMessage
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.store import MemoryStore
from agent_memory.short_term.conversation.memory import ConversationMemory


class AgentRunner:
    def __init__(
        self,
        conversation_memory: ConversationMemory,
        memory_store: MemoryStore | None = None,
        context_builder: MemoryContextBuilder | None = None,
        extractor: MemoryExtractor | None = None,
    ) -> None:
        self._conversation_memory = conversation_memory
        self._memory_store = memory_store
        self._context_builder = context_builder
        self._extractor = extractor

    def run(
        self,
        agent: Agent,
        session: AgentSession,
        user_input: str,
    ) -> AgentResult:
        run_id = str(uuid4())
        started_at = utc_now()

        if agent.tools:
            raise AgentRunError(
                "Tool execution is not implemented by AgentRunner yet."
            )

        previous_items = self._conversation_memory.get_items(session.thread_id)
        previous_last_item_id = previous_items[-1].id if previous_items else None
        self._conversation_memory.add_message(
            thread_id=session.thread_id,
            role="user",
            content=user_input,
        )
        memory_context = self._build_memory_context(
            session=session,
            query=user_input,
        )
        model_messages = self._build_model_messages(
            agent=agent,
            thread_id=session.thread_id,
            memory_context=memory_context,
        )
        response = agent.model.invoke(model_messages)
        assistant_message = self._conversation_memory.add_message(
            thread_id=session.thread_id,
            role="assistant",
            content=response.content,
            model_name=optional_string(response.metadata.get("model")),
            usage=response.usage,
            metadata=response.metadata,
        )
        output = parse_agent_output(
            raw_output=response.content,
            output_schema=agent.output_schema,
        )
        extracted_records = self._extract_and_store_records(
            session=session,
            since_item_id=previous_last_item_id,
        )

        finished_at = utc_now()

        return AgentResult(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms(started_at, finished_at),
            assistant_message=assistant_message,
            output=output,
            raw_output=response.content,
            memory_context=memory_context,
            extracted_records=extracted_records,
            tool_calls=[],
            tool_results=[],
            usage=response.usage,
            metadata=response.metadata,
        )

    def _build_memory_context(
        self,
        session: AgentSession,
        query: str,
    ) -> MemoryContextResult | None:
        if self._context_builder is None or session.namespace is None:
            return None

        context = self._context_builder.build(
            MemoryContextRequest(
                namespace=session.namespace,
                query=query,
            )
        )

        if not context.has_content:
            return None

        return context

    def _build_model_messages(
        self,
        agent: Agent,
        thread_id: str,
        memory_context: MemoryContextResult | None,
    ) -> list[LLMMessage]:
        messages: list[LLMMessage] = [
            SystemMessage(content=agent.instructions),
        ]

        if memory_context is not None:
            messages.append(
                SystemMessage(content=memory_context.content)
            )

        conversation_messages = self._conversation_memory.get_messages(thread_id)
        messages.extend(to_llm_messages(conversation_messages))

        return messages

    def _extract_and_store_records(
        self,
        session: AgentSession,
        since_item_id: str | None,
    ) -> list[LongTermRecord]:
        if (
            self._extractor is None
            or self._memory_store is None
            or session.namespace is None
        ):
            return []

        conversation = self._conversation_memory.get_thread(session.thread_id)
        extraction = self._extractor.extract(
            MemoryExtractionRequest(
                namespace=session.namespace,
                conversation=conversation,
                since_item_id=since_item_id,
            )
        )

        for record in extraction.records:
            self._memory_store.put(record)

        return extraction.records


def parse_agent_output(
    raw_output: str,
    output_schema: type[BaseModel] | None,
) -> AgentOutput:
    if output_schema is None:
        return raw_output

    try:
        payload = parse_json_object(raw_output)
        return output_schema.model_validate(payload)
    except (ValueError, ValidationError) as error:
        raise AgentOutputValidationError(
            "Failed to validate agent structured output."
        ) from error


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()

    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").removesuffix("```").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").removesuffix("```").strip()

    payload = json.loads(stripped)

    if not isinstance(payload, dict):
        raise ValueError("Agent structured output must be a JSON object.")

    return payload


def optional_string(value: object) -> str | None:
    if value is None:
        return None

    return str(value)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)
