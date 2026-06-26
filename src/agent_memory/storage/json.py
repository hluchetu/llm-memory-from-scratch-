from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_memory.short_term.conversation.state import ConversationItem
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import SummaryItem


class JsonStorage:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            self._write_data({})

    def get(self, thread_id: str) -> ConversationState | None:
        data = self._read_data()
        raw_state = data.get(thread_id)

        if raw_state is None:
            return None

        return self._deserialize_state(raw_state)

    def save(self, state: ConversationState) -> None:
        data = self._read_data()
        data[state.thread_id] = self._serialize_state(state)
        self._write_data(data)

    def create_thread(self, thread_id: str) -> None:
        data = self._read_data()

        if thread_id not in data:
            data[thread_id] = self._serialize_state(
                ConversationState(thread_id=thread_id)
            )
            self._write_data(data)

    def append_message(self, thread_id: str, message: Message) -> None:
        self.append_item(thread_id, message)

    def append_item(self, thread_id: str, item: ConversationItem) -> None:
        state = self.get(thread_id)

        if state is None:
            state = ConversationState(thread_id=thread_id)

        state.items.append(item)
        self.save(state)

    def replace_items(
        self,
        thread_id: str,
        items: list[ConversationItem],
    ) -> None:
        self.save(
            ConversationState(
                thread_id=thread_id,
                items=items,
            )
        )

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self.replace_items(thread_id, messages)

    def delete(self, thread_id: str) -> None:
        data = self._read_data()
        data.pop(thread_id, None)
        self._write_data(data)

    def _read_data(self) -> dict[str, Any]:
        content = self._path.read_text(encoding="utf-8")

        if not content.strip():
            return {}

        return json.loads(content)

    def _write_data(self, data: dict[str, Any]) -> None:
        self._path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def _serialize_state(self, state: ConversationState) -> dict[str, Any]:
        return {
            "thread_id": state.thread_id,
            "items": [
                self._serialize_item(item)
                for item in state.items
            ],
        }

    def _deserialize_state(self, raw_state: dict[str, Any]) -> ConversationState:
        return ConversationState(
            thread_id=raw_state["thread_id"],
            items=[
                self._deserialize_item(raw_item)
                for raw_item in raw_state.get("items", raw_state.get("messages", []))
            ],
        )

    def _serialize_item(self, item: ConversationItem) -> dict[str, Any]:
        if isinstance(item, Message):
            return {
                "item_type": "message",
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at.isoformat(),
                "pinned": item.pinned,
                "run_id": item.run_id,
                "model_name": item.model_name,
                "usage": item.usage,
                "metadata": item.metadata,
            }

        if isinstance(item, SummaryItem):
            return {
                "item_type": "summary",
                "id": item.id,
                "content": item.content,
                "created_at": item.created_at.isoformat(),
                "pinned": item.pinned,
                "covered_item_ids": item.covered_item_ids,
                "metadata": item.metadata,
            }

        return {
            "item_type": getattr(item, "item_type", "unknown"),
            "id": item.id,
            "created_at": item.created_at.isoformat(),
            "pinned": item.pinned,
            "metadata": item.metadata,
        }

    def _deserialize_item(self, raw_item: dict[str, Any]) -> ConversationItem:
        item_type = raw_item.get("item_type", "message")

        if item_type == "summary":
            return SummaryItem(
                id=raw_item["id"],
                content=raw_item["content"],
                created_at=datetime.fromisoformat(raw_item["created_at"]),
                pinned=bool(raw_item.get("pinned", False)),
                covered_item_ids=raw_item.get("covered_item_ids", []),
                metadata=raw_item.get("metadata", {}),
            )

        return Message(
            id=raw_item["id"],
            role=raw_item["role"],
            content=raw_item["content"],
            created_at=datetime.fromisoformat(raw_item["created_at"]),
            pinned=bool(raw_item.get("pinned", False)),
            run_id=raw_item.get("run_id"),
            model_name=raw_item.get("model_name"),
            usage=raw_item.get("usage"),
            metadata=raw_item.get("metadata", {}),
        )
