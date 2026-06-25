from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_memory.errors import MemoryExtractionError
from agent_memory.extraction.interface import MemoryExtractionRequest
from agent_memory.extraction.interface import MemoryExtractionResult
from agent_memory.extraction.triggers import ExtractionTrigger
from agent_memory.llm.interface import ChatModel
from agent_memory.llm.message import HumanMessage
from agent_memory.llm.message import SystemMessage
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.item import utc_now
from agent_memory.long_term.decision import DecisionMemory
from agent_memory.long_term.episodic import EventMemory
from agent_memory.long_term.preference import PreferenceMemory
from agent_memory.long_term.procedural import WorkflowMemory
from agent_memory.long_term.semantic import EntityMemory
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.prompts.loader import load_prompt
from agent_memory.short_term.conversation.state import ConversationItem
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import RetrievalItem
from agent_memory.short_term.conversation.state import SummaryItem
from agent_memory.short_term.conversation.state import ToolCall
from agent_memory.short_term.conversation.state import ToolResult


class LLMMemoryExtractor:
    def __init__(
        self,
        model: ChatModel,
        trigger: ExtractionTrigger | None = None,
    ) -> None:
        self._model = model
        self._trigger = trigger

    def extract(self, request: MemoryExtractionRequest) -> MemoryExtractionResult:
        if self._trigger is not None and not self._trigger.should_extract(request.conversation):
            return MemoryExtractionResult(
                records=[],
                source_item_ids=[],
                skipped_reason="Extraction skipped by trigger.",
            )

        items = select_items(
            conversation=request.conversation,
            since_item_id=request.since_item_id,
            max_items=request.max_items,
        )

        if not items:
            return MemoryExtractionResult(
                records=[],
                source_item_ids=[],
                skipped_reason="No conversation items to extract from.",
            )

        prompt = load_prompt(
            file_name="memory_extraction.yaml",
            prompt_name="memory_extraction",
        )
        source_item_ids = [item.id for item in items]

        try:
            response = self._model.invoke(
                [
                    SystemMessage(content=prompt["system"]),
                    HumanMessage(
                        content=prompt["user"].format(
                            namespace="/".join(request.namespace),
                            conversation=format_items(items),
                        )
                    ),
                ]
            )
            payload = parse_json_object(response.content)
            records = build_records(
                payload=payload,
                namespace=request.namespace,
                source_item_ids=source_item_ids,
            )
        except Exception as error:
            raise MemoryExtractionError(
                "Failed to extract long-term memory records."
            ) from error

        if not records:
            return MemoryExtractionResult(
                records=[],
                source_item_ids=source_item_ids,
                skipped_reason="Model returned no durable memory records.",
            )

        return MemoryExtractionResult(
            records=records,
            source_item_ids=source_item_ids,
        )


def select_items(
    conversation: ConversationState,
    since_item_id: str | None,
    max_items: int | None,
) -> list[ConversationItem]:
    if max_items is not None and max_items <= 0:
        raise ValueError("max_items must be greater than 0.")

    items = conversation.items

    if since_item_id is not None:
        start_index = next(
            (
                index + 1
                for index, item in enumerate(items)
                if item.id == since_item_id
            ),
            0,
        )
        items = items[start_index:]

    if max_items is not None:
        items = items[-max_items:]

    return items


def format_items(items: list[ConversationItem]) -> str:
    lines: list[str] = []

    for item in items:
        lines.append(format_item(item))

    return "\n".join(lines)


def format_item(item: ConversationItem) -> str:
    if isinstance(item, Message):
        return f"[{item.id}] {item.role}: {item.content}"

    if isinstance(item, ToolCall):
        return f"[{item.id}] tool_call {item.name}: {item.arguments}"

    if isinstance(item, ToolResult):
        return f"[{item.id}] tool_result {item.name}: {item.content}"

    if isinstance(item, RetrievalItem):
        return f"[{item.id}] retrieval {item.query}: {item.content}"

    if isinstance(item, SummaryItem):
        return f"[{item.id}] summary: {item.content}"

    return f"[{item.id}] item: {item}"


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()

    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").removesuffix("```").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").removesuffix("```").strip()

    payload = json.loads(stripped)

    if not isinstance(payload, dict):
        raise ValueError("Memory extraction response must be a JSON object.")

    return payload


def build_records(
    payload: dict[str, Any],
    namespace: tuple[str, ...],
    source_item_ids: list[str],
) -> list[LongTermRecord]:
    raw_records = payload.get("records") or []

    if not isinstance(raw_records, list):
        raise ValueError("Memory extraction records must be a list.")

    records: list[LongTermRecord] = []

    for raw_record in raw_records:
        if not isinstance(raw_record, dict):
            continue

        records.append(
            build_record(
                raw_record=raw_record,
                namespace=namespace,
                source_item_ids=source_item_ids,
            )
        )

    return records


def build_record(
    raw_record: dict[str, Any],
    namespace: tuple[str, ...],
    source_item_ids: list[str],
) -> LongTermRecord:
    record_type = str(raw_record.get("record_type", "")).strip().lower()
    common_fields = {
        "namespace": namespace,
        "key": required_string(raw_record, "key"),
        "importance": optional_float(raw_record.get("importance")),
        "metadata": build_metadata(raw_record, source_item_ids),
    }

    if record_type == "knowledge":
        return KnowledgeMemory(
            **common_fields,
            content=required_string(raw_record, "content"),
            source=optional_string(raw_record.get("source")),
        )

    if record_type == "entity":
        return EntityMemory(
            **common_fields,
            name=required_string(raw_record, "name"),
            description=required_string(raw_record, "description"),
        )

    if record_type == "event":
        return EventMemory(
            **common_fields,
            description=required_string(raw_record, "description"),
            occurred_at=parse_datetime(
                optional_string(raw_record.get("occurred_at")) or utc_now()
            ),
        )

    if record_type == "workflow":
        return WorkflowMemory(
            **common_fields,
            steps=required_string_list(raw_record, "steps"),
        )

    if record_type == "preference":
        return PreferenceMemory(
            **common_fields,
            subject=required_string(raw_record, "subject"),
            preference=required_string(raw_record, "preference"),
            confidence=float(raw_record.get("confidence") or 1.0),
        )

    if record_type == "decision":
        return DecisionMemory(
            **common_fields,
            decision=required_string(raw_record, "decision"),
            rationale=optional_string(raw_record.get("rationale")),
            outcome=optional_string(raw_record.get("outcome")),
        )

    raise ValueError(f"Unsupported extracted record type: {record_type}")


def build_metadata(
    raw_record: dict[str, Any],
    source_item_ids: list[str],
) -> dict[str, Any]:
    metadata = raw_record.get("metadata") or {}

    if not isinstance(metadata, dict):
        metadata = {}

    return {
        **metadata,
        "source_item_ids": source_item_ids,
        "extracted_by": "llm",
    }


def required_string(raw_record: dict[str, Any], field_name: str) -> str:
    value = raw_record.get(field_name)

    if value is None:
        raise ValueError(f"Extracted record is missing {field_name}.")

    text = str(value).strip()

    if not text:
        raise ValueError(f"Extracted record has empty {field_name}.")

    return text


def optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def required_string_list(
    raw_record: dict[str, Any],
    field_name: str,
) -> list[str]:
    value = raw_record.get(field_name)

    if not isinstance(value, list):
        raise ValueError(f"Extracted record {field_name} must be a list.")

    strings = [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]

    if not strings:
        raise ValueError(f"Extracted record has empty {field_name}.")

    return strings


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value

    return datetime.fromisoformat(str(value))


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
        return max(0.0, min(1.0, result))
    except (TypeError, ValueError):
        return None
