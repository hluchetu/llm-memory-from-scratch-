from __future__ import annotations

from typing import Literal

from agent_memory.bridge import ProviderMessage
from agent_memory.bridge import messages_to_conversation_state
from agent_memory.context.interface import MemoryContextResult
from agent_memory.extraction.interface import MemoryExtractionResult
from agent_memory.long_term.item import LongTermRecord
from agent_memory.manager import MemoryManager


MessageRole = Literal["system", "user", "assistant"]


class GenericMemoryAdapter:
    def __init__(
        self,
        manager: MemoryManager,
        strict_messages: bool = False,
    ) -> None:
        self._manager = manager
        self._strict_messages = strict_messages

    def extract(
        self,
        messages: list[ProviderMessage],
        namespace: tuple[str, ...],
        thread_id: str,
        since_item_id: str | None = None,
        strict_messages: bool | None = None,
    ) -> MemoryExtractionResult:
        conversation = messages_to_conversation_state(
            messages,
            thread_id=thread_id,
            strict=self._resolve_strict_messages(strict_messages),
        )
        return self._manager.extract(
            conversation=conversation,
            namespace=namespace,
            since_item_id=since_item_id,
        )

    async def extract_async(
        self,
        messages: list[ProviderMessage],
        namespace: tuple[str, ...],
        thread_id: str,
        since_item_id: str | None = None,
        strict_messages: bool | None = None,
    ) -> MemoryExtractionResult:
        conversation = messages_to_conversation_state(
            messages,
            thread_id=thread_id,
            strict=self._resolve_strict_messages(strict_messages),
        )
        return await self._manager.extract_async(
            conversation=conversation,
            namespace=namespace,
            since_item_id=since_item_id,
        )

    def inject(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
    ) -> MemoryContextResult:
        return self._manager.inject(
            query=query,
            namespace=namespace,
            limit=limit,
        )

    async def inject_async(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
    ) -> MemoryContextResult:
        return await self._manager.inject_async(
            query=query,
            namespace=namespace,
            limit=limit,
        )

    def inject_message(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
        role: MessageRole = "system",
    ) -> ProviderMessage | None:
        result = self.inject(
            query=query,
            namespace=namespace,
            limit=limit,
        )

        if not result.has_content:
            return None

        return {
            "role": role,
            "content": result.content,
        }

    async def inject_message_async(
        self,
        query: str,
        namespace: tuple[str, ...],
        limit: int = 5,
        role: MessageRole = "system",
    ) -> ProviderMessage | None:
        result = await self.inject_async(
            query=query,
            namespace=namespace,
            limit=limit,
        )

        if not result.has_content:
            return None

        return {
            "role": role,
            "content": result.content,
        }

    def search(
        self,
        query: str,
        namespace: tuple[str, ...],
        store_name: str | None = None,
        limit: int = 5,
    ) -> list[LongTermRecord]:
        return self._manager.search(
            query=query,
            namespace=namespace,
            store_name=store_name,
            limit=limit,
        )

    async def search_async(
        self,
        query: str,
        namespace: tuple[str, ...],
        store_name: str | None = None,
        limit: int = 5,
    ) -> list[LongTermRecord]:
        return await self._manager.search_async(
            query=query,
            namespace=namespace,
            store_name=store_name,
            limit=limit,
        )

    def _resolve_strict_messages(self, strict_messages: bool | None) -> bool:
        if strict_messages is None:
            return self._strict_messages

        return strict_messages
