from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from agent_memory.short_term.conversation.state import ConversationItem
from agent_memory.short_term.conversation.state import ConversationState
from agent_memory.short_term.conversation.state import Message
from agent_memory.short_term.conversation.state import SummaryItem


class SQLiteStorage:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def get(self, thread_id: str) -> ConversationState | None:
        with self._connect() as connection:
            conversation = connection.execute(
                """
                SELECT id
                FROM conversations
                WHERE id = ?
                """,
                (thread_id,),
            ).fetchone()

            if conversation is None:
                return None

            rows = connection.execute(
                """
                SELECT
                    id,
                    item_type,
                    role,
                    content,
                    created_at,
                    run_id,
                    model_name,
                    usage,
                    metadata
                FROM conversation_items
                WHERE conversation_id = ?
                ORDER BY position ASC
                """,
                (thread_id,),
            ).fetchall()

        return ConversationState(
            thread_id=thread_id,
            items=[
                self._row_to_item(row)
                for row in rows
            ],
        )

    def save(self, state: ConversationState) -> None:
        self.replace_items(
            thread_id=state.thread_id,
            items=state.items,
        )

    def create_thread(self, thread_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, created_at, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO NOTHING
                """,
                (thread_id,),
            )

    def append_message(self, thread_id: str, message: Message) -> None:
        self.append_item(thread_id, message)

    def append_item(self, thread_id: str, item: ConversationItem) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, created_at, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
                """,
                (thread_id,),
            )

            position = connection.execute(
                """
                SELECT COALESCE(MAX(position) + 1, 0) AS next_position
                FROM conversation_items
                WHERE conversation_id = ?
                """,
                (thread_id,),
            ).fetchone()["next_position"]

            self._insert_item(connection, thread_id, position, item)

    def replace_items(
        self,
        thread_id: str,
        items: list[ConversationItem],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, created_at, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
                """,
                (thread_id,),
            )

            connection.execute(
                "DELETE FROM conversation_items WHERE conversation_id = ?",
                (thread_id,),
            )

            for position, item in enumerate(items):
                self._insert_item(connection, thread_id, position, item)

    def replace_messages(self, thread_id: str, messages: list[Message]) -> None:
        self.replace_items(thread_id, messages)

    def delete(self, thread_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (thread_id,),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def _insert_item(
        self,
        connection: sqlite3.Connection,
        thread_id: str,
        position: int,
        item: ConversationItem,
    ) -> None:
        if isinstance(item, Message):
            item_type = "message"
            role = item.role
            content = item.content
            run_id = item.run_id
            model_name = item.model_name
            usage = item.usage or {}
            metadata = item.metadata
        elif isinstance(item, SummaryItem):
            item_type = "summary"
            role = None
            content = item.content
            run_id = None
            model_name = None
            usage = {}
            metadata = {
                "metadata": item.metadata,
                "covered_item_ids": item.covered_item_ids,
            }
        else:
            item_type = getattr(item, "item_type", "unknown")
            role = None
            content = ""
            run_id = None
            model_name = None
            usage = {}
            metadata = item.metadata

        connection.execute(
            """
            INSERT INTO conversation_items (
                id,
                conversation_id,
                item_type,
                position,
                role,
                content,
                created_at,
                run_id,
                model_name,
                usage,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                thread_id,
                item_type,
                position,
                role,
                content,
                item.created_at.isoformat(),
                run_id,
                model_name,
                json.dumps(usage),
                json.dumps(metadata),
            ),
        )

    def _row_to_item(self, row: sqlite3.Row) -> ConversationItem:
        metadata = json.loads(row["metadata"])

        if row["item_type"] == "summary":
            return SummaryItem(
                id=row["id"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
                covered_item_ids=metadata.get("covered_item_ids", []),
                metadata=metadata.get("metadata", {}),
            )

        return Message(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            run_id=row["run_id"],
            model_name=row["model_name"],
            usage=json.loads(row["usage"]),
            metadata=metadata,
        )

    def _create_tables(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (id)
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_items (
                    id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    item_type TEXT NOT NULL CHECK (
                        item_type IN (
                            'message',
                            'tool_call',
                            'tool_result',
                            'retrieval',
                            'summary'
                        )
                    ),
                    position INTEGER NOT NULL,
                    role TEXT CHECK (
                        role IN ('system', 'user', 'assistant', 'tool')
                    ),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    run_id TEXT,
                    model_name TEXT,
                    usage TEXT NOT NULL DEFAULT '{}',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (id),
                    UNIQUE (conversation_id, position),
                    CHECK (item_type != 'message' OR role IS NOT NULL),
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE CASCADE
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_items_lookup
                ON conversation_items (conversation_id, position)
                """
            )
