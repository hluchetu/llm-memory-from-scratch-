from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from llm_memory.conversation.state import ConversationState
from llm_memory.conversation.state import Message


class MarkdownStorage:
    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def get(self, thread_id: str) -> ConversationState | None:
        path = self._path_for_thread(thread_id)

        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")
        messages = self._parse_messages(content)

        return ConversationState(
            thread_id=thread_id,
            messages=messages,
        )

    def save(self, state: ConversationState) -> None:
        path = self._path_for_thread(state.thread_id)
        path.write_text(
            self._serialize_state(state),
            encoding="utf-8",
        )

    def create_thread(self, thread_id: str) -> None:
        path = self._path_for_thread(thread_id)

        if not path.exists():
            self.save(ConversationState(thread_id=thread_id))

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
        path = self._path_for_thread(thread_id)

        if path.exists():
            path.unlink()

    def _path_for_thread(self, thread_id: str) -> Path:
        safe_thread_id = thread_id.replace("/", "-")

        return self._directory / f"{safe_thread_id}.md"

    def _serialize_state(self, state: ConversationState) -> str:
        lines = [
            f"# Conversation: {state.thread_id}",
            "",
        ]

        for message in state.messages:
            lines.extend(
                [
                    "## Message",
                    "",
                    f"id: {message.id}",
                    f"role: {message.role}",
                    f"created_at: {message.created_at.isoformat()}",
                    f"run_id: {message.run_id or ''}",
                    f"model_name: {message.model_name or ''}",
                    f"usage: {json.dumps(message.usage or {})}",
                    f"metadata: {json.dumps(message.metadata)}",
                    "",
                    message.content,
                    "",
                ]
            )

        return "\n".join(lines)

    def _parse_messages(self, content: str) -> list[Message]:
        sections = content.split("## Message")
        messages: list[Message] = []

        for section in sections[1:]:
            message = self._parse_message(section)

            if message is not None:
                messages.append(message)

        return messages

    def _parse_message(self, section: str) -> Message | None:
        stripped_section = section.strip()

        if not stripped_section:
            return None

        metadata_block, _, message_content = stripped_section.partition("\n\n")
        metadata = self._parse_metadata(metadata_block)

        message_id = metadata.get("id")
        role = metadata.get("role")
        created_at = metadata.get("created_at")
        run_id = metadata.get("run_id") or None
        model_name = metadata.get("model_name") or None
        usage = json.loads(metadata.get("usage", "{}"))
        message_metadata = json.loads(metadata.get("metadata", "{}"))

        if message_id is None or role is None or created_at is None:
            return None

        return Message(
            id=message_id,
            role=role,  # type: ignore[arg-type]
            content=message_content.strip(),
            created_at=datetime.fromisoformat(created_at),
            run_id=run_id,
            model_name=model_name,
            usage=usage,
            metadata=message_metadata,
        )

    def _parse_metadata(self, metadata_block: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        for line in metadata_block.splitlines():
            key, separator, value = line.partition(":")

            if separator:
                metadata[key.strip()] = value.strip()

        return metadata
