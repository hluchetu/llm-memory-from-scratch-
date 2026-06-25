from __future__ import annotations

from typing import Protocol

from agent_memory.long_term.item import LongTermRecord


class MemoryStorage(Protocol):
    def put(self, record: LongTermRecord) -> None:
        ...

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> LongTermRecord | None:
        ...

    def get_by_id(self, record_id: str) -> LongTermRecord | None:
        ...

    def get_many(self, ids: list[str]) -> list[LongTermRecord]:
        ...

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        ...


class InMemoryStorage:
    def __init__(self) -> None:
        self._records_by_key: dict[tuple[tuple[str, ...], str], LongTermRecord] = {}
        self._records_by_id: dict[str, LongTermRecord] = {}

    def put(self, record: LongTermRecord) -> None:
        lookup_key = (record.namespace, record.key)
        previous_record = self._records_by_key.get(lookup_key)

        if previous_record is not None:
            self._records_by_id.pop(previous_record.id, None)

        self._records_by_key[lookup_key] = record
        self._records_by_id[record.id] = record

    def get(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> LongTermRecord | None:
        return self._records_by_key.get((namespace, key))

    def get_by_id(self, record_id: str) -> LongTermRecord | None:
        return self._records_by_id.get(record_id)

    def get_many(self, ids: list[str]) -> list[LongTermRecord]:
        records: list[LongTermRecord] = []

        for record_id in ids:
            record = self._records_by_id.get(record_id)

            if record is not None:
                records.append(record)

        return records

    def delete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        record = self._records_by_key.pop((namespace, key), None)

        if record is None:
            return

        self._records_by_id.pop(record.id, None)
