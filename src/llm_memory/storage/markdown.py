from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from llm_memory.context.conversation.state import ConversationItem
from llm_memory.context.conversation.state import ConversationState
from llm_memory.context.conversation.state import Message
from llm_memory.context.conversation.state import SummaryItem


class MarkdownStorage:
    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def get(self, thread_id: str) -> ConversationState | None:
        path = self._path_for_thread(thread_id)

        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")
        items = self._parse_items(content)

        return ConversationState(
            thread_id=thread_id,
            items=items,
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

        for item in state.items:
            if isinstance(item, Message):
                lines.extend(self._serialize_message(item))
            elif isinstance(item, SummaryItem):
                lines.extend(self._serialize_summary(item))

        return "\n".join(lines)

    def _serialize_message(self, message: Message) -> list[str]:
        return [
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

    def _serialize_summary(self, summary: SummaryItem) -> list[str]:
        return [
            "## Summary",
            "",
            f"id: {summary.id}",
            f"created_at: {summary.created_at.isoformat()}",
            f"covered_item_ids: {json.dumps(summary.covered_item_ids)}",
            f"metadata: {json.dumps(summary.metadata)}",
            "",
            summary.content,
            "",
        ]

    def _parse_items(self, content: str) -> list[ConversationItem]:
        sections = content.split("## ")
        items: list[ConversationItem] = []

        for section in sections[1:]:
            title, _, body = section.partition("\n")
            item = None

            if title.strip() == "Message":
                item = self._parse_message(body)
            elif title.strip() == "Summary":
                item = self._parse_summary(body)

            if item is not None:
                items.append(item)

        return items

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

    def _parse_summary(self, section: str) -> SummaryItem | None:
        stripped_section = section.strip()

        if not stripped_section:
            return None

        metadata_block, _, summary_content = stripped_section.partition("\n\n")
        metadata = self._parse_metadata(metadata_block)

        summary_id = metadata.get("id")
        created_at = metadata.get("created_at")
        covered_item_ids = json.loads(metadata.get("covered_item_ids", "[]"))
        summary_metadata = json.loads(metadata.get("metadata", "{}"))

        if summary_id is None or created_at is None:
            return None

        return SummaryItem(
            id=summary_id,
            content=summary_content.strip(),
            created_at=datetime.fromisoformat(created_at),
            covered_item_ids=covered_item_ids,
            metadata=summary_metadata,
        )

    def _parse_metadata(self, metadata_block: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        for line in metadata_block.splitlines():
            key, separator, value = line.partition(":")

            if separator:
                metadata[key.strip()] = value.strip()

        return metadata
