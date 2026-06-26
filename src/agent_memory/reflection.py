from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from agent_memory.context.long_term import format_record
from agent_memory.llm.interface import ChatModel
from agent_memory.llm.message import HumanMessage
from agent_memory.llm.message import SystemMessage
from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.store import MemoryStore
from agent_memory.prompts.loader import load_prompt
from agent_memory.utils.asyncio import run_sync
from agent_memory.utils.json import parse_json_object


@dataclass(frozen=True, kw_only=True)
class ReflectionResult:
    records: list[KnowledgeMemory]
    source_record_ids: list[str]
    skipped_reason: str | None = None


@dataclass
class MemoryReflector:
    memory_store: MemoryStore
    model: ChatModel
    reflection_interval: int = 10
    importance_threshold: float = 3.0
    source_limit: int = 20
    _pending_record_count: int = field(default=0, init=False)
    _pending_importance_sum: float = field(default=0.0, init=False)

    def observe(
        self,
        records: list[LongTermRecord],
        namespace: tuple[str, ...],
    ) -> ReflectionResult | None:
        self._pending_record_count += len(records)
        self._pending_importance_sum += sum(record.importance or 0.0 for record in records)

        if not self.should_reflect():
            return None

        result = self.reflect(namespace)
        self._pending_record_count = 0
        self._pending_importance_sum = 0.0
        return result

    async def observe_async(
        self,
        records: list[LongTermRecord],
        namespace: tuple[str, ...],
    ) -> ReflectionResult | None:
        return await run_sync(self.observe, records, namespace)

    def should_reflect(self) -> bool:
        return (
            self._pending_record_count >= self.reflection_interval
            or self._pending_importance_sum >= self.importance_threshold
        )

    def reflect(self, namespace: tuple[str, ...]) -> ReflectionResult:
        source_records = select_reflection_sources(
            self.memory_store.list(namespace=namespace),
            limit=self.source_limit,
        )

        if not source_records:
            return ReflectionResult(
                records=[],
                source_record_ids=[],
                skipped_reason="No source memories available for reflection.",
            )

        prompt = load_prompt(
            file_name="memory_reflection.yaml",
            prompt_name="memory_reflection",
        )
        messages = [
            SystemMessage(content=prompt["system"]),
            HumanMessage(
                content=prompt["user"].format(
                    namespace="/".join(namespace),
                    memories=format_source_memories(source_records),
                )
            ),
        ]
        response = self.model.invoke(messages)
        records = build_reflection_records(
            payload=parse_json_object(
                response.content,
                error_message="Memory reflection response must be a JSON object.",
            ),
            namespace=namespace,
            source_records=source_records,
        )

        for record in records:
            self.memory_store.put(record)

        if not records:
            return ReflectionResult(
                records=[],
                source_record_ids=[record.id for record in source_records],
                skipped_reason="Model returned no durable reflection insights.",
            )

        return ReflectionResult(
            records=records,
            source_record_ids=[record.id for record in source_records],
        )

    async def reflect_async(
        self,
        namespace: tuple[str, ...],
    ) -> ReflectionResult:
        return await run_sync(self.reflect, namespace)


def select_reflection_sources(
    records: list[LongTermRecord],
    limit: int,
) -> list[LongTermRecord]:
    candidates = [
        record
        for record in records
        if record.invalidated_at is None
        and record.metadata.get("source") != "reflection"
    ]
    candidates.sort(
        key=lambda record: (
            record.importance or 0.0,
            record.created_at,
        ),
        reverse=True,
    )
    return candidates[:limit]


def format_source_memories(records: list[LongTermRecord]) -> str:
    lines = []

    for record in records:
        lines.append(
            f"- key={record.key} type={record.memory_type} "
            f"importance={record.importance if record.importance is not None else 'unknown'}: "
            f"{format_record(record)}"
        )

    return "\n".join(lines)


def build_reflection_records(
    payload: dict[str, Any],
    namespace: tuple[str, ...],
    source_records: list[LongTermRecord],
) -> list[KnowledgeMemory]:
    raw_insights = payload.get("insights") or []

    if not isinstance(raw_insights, list):
        raise ValueError("Memory reflection insights must be a list.")

    records_by_key = {record.key: record for record in source_records}
    records: list[KnowledgeMemory] = []

    for raw_insight in raw_insights:
        if not isinstance(raw_insight, dict):
            continue

        key = optional_string(raw_insight.get("key"))
        content = optional_string(raw_insight.get("content"))

        if key is None or content is None:
            continue

        supporting_keys = [
            str(value).strip()
            for value in raw_insight.get("supporting_keys") or []
            if str(value).strip()
        ]
        supporting_record_ids = [
            records_by_key[supporting_key].id
            for supporting_key in supporting_keys
            if supporting_key in records_by_key
        ]

        records.append(
            KnowledgeMemory(
                namespace=namespace,
                key=key,
                content=content,
                source="reflection",
                importance=optional_float(raw_insight.get("importance")),
                metadata={
                    "source": "reflection",
                    "supporting_keys": supporting_keys,
                    "supporting_record_ids": supporting_record_ids,
                },
                related_ids=tuple(supporting_record_ids),
            )
        )

    return records


def optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
        return max(0.0, min(1.0, result))
    except (TypeError, ValueError):
        return None
