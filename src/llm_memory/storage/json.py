from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_memory.conversation.state import ConversationState
from llm_memory.conversation.state import Message


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
        state = self.get(thread_id)

        if state is None:
            state = ConversationState(thread_id=thread_id)

        state.messages.append(message)
        self.save(state)

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self.save(
            ConversationState(
                thread_id=thread_id,
                messages=messages,
            )
        )

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
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "run_id": message.run_id,
                    "model_name": message.model_name,
                    "usage": message.usage,
                    "metadata": message.metadata,
                }
                for message in state.messages
            ],
        }

    def _deserialize_state(self, raw_state: dict[str, Any]) -> ConversationState:
        return ConversationState(
            thread_id=raw_state["thread_id"],
            messages=[
                Message(
                    id=raw_message["id"],
                    role=raw_message["role"],
                    content=raw_message["content"],
                    created_at=datetime.fromisoformat(raw_message["created_at"]),
                    run_id=raw_message.get("run_id"),
                    model_name=raw_message.get("model_name"),
                    usage=raw_message.get("usage"),
                    metadata=raw_message.get("metadata", {}),
                )
                for raw_message in raw_state["messages"]
            ],
        )
