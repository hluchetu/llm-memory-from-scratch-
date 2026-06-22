from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent_memory.long_term.item import LongTermRecord
from agent_memory.long_term.serialization import record_from_dict
from agent_memory.long_term.serialization import record_to_dict


class SQLiteMemoryStorage:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def put(self, record: LongTermRecord) -> None:
        payload = record_to_dict(record)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO long_term_records (
                    id,
                    namespace,
                    key,
                    memory_type,
                    record_type,
                    created_at,
                    metadata_json,
                    record_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    id = excluded.id,
                    memory_type = excluded.memory_type,
                    record_type = excluded.record_type,
                    created_at = excluded.created_at,
                    metadata_json = excluded.metadata_json,
                    record_json = excluded.record_json
                """,
                (
                    record.id,
                    serialize_namespace(record.namespace),
                    record.key,
                    record.memory_type,
                    str(payload["record_type"]),
                    str(payload["created_at"]),
                    json.dumps(payload["metadata"]),
                    json.dumps(payload),
                ),
            )

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> LongTermRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT record_json
                FROM long_term_records
                WHERE namespace = ? AND key = ?
                """,
                (serialize_namespace(namespace), key),
            ).fetchone()

        if row is None:
            return None

        return record_from_dict(json.loads(str(row["record_json"])))

    def get_many(self, ids: list[str]) -> list[LongTermRecord]:
        if not ids:
            return []

        placeholders = ", ".join("?" for _ in ids)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, record_json
                FROM long_term_records
                WHERE id IN ({placeholders})
                """,
                ids,
            ).fetchall()

        records_by_id = {
            str(row["id"]): record_from_dict(json.loads(str(row["record_json"])))
            for row in rows
        }

        return [
            records_by_id[record_id]
            for record_id in ids
            if record_id in records_by_id
        ]

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM long_term_records
                WHERE namespace = ? AND key = ?
                """,
                (serialize_namespace(namespace), key),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS long_term_records (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    UNIQUE(namespace, key)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_long_term_records_memory_type
                ON long_term_records(memory_type)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_long_term_records_created_at
                ON long_term_records(created_at)
                """
            )


def serialize_namespace(namespace: tuple[str, ...]) -> str:
    return json.dumps(list(namespace))
