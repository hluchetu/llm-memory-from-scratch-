from __future__ import annotations

import pytest

from agent_memory.extraction.interface import MemoryExtractionRequest
from agent_memory.extraction.interface import MemoryExtractionResult
from agent_memory.integrations import GenericMemoryAdapter
from agent_memory.long_term.semantic import KnowledgeMemory
from agent_memory.long_term.storage import InMemoryStorage
from agent_memory.long_term.store import MemoryStore
from agent_memory.manager import MemoryManager
from agent_memory.manager import MemoryStoreConfig
from agent_memory.retrieval.lexical import LexicalMemoryRetriever


class RecordingExtractor:
    def __init__(self) -> None:
        self.requests: list[MemoryExtractionRequest] = []

    def extract(
        self,
        request: MemoryExtractionRequest,
    ) -> MemoryExtractionResult:
        self.requests.append(request)
        return MemoryExtractionResult(
            records=[
                KnowledgeMemory(
                    id="preference",
                    namespace=request.namespace,
                    key="answer_style",
                    content="User prefers concise answers.",
                )
            ],
            source_item_ids=[item.id for item in request.conversation.items],
        )


def build_adapter(
    extractor: RecordingExtractor | None = None,
) -> tuple[GenericMemoryAdapter, MemoryStore]:
    store = MemoryStore(
        storage=InMemoryStorage(),
        retrievers=[LexicalMemoryRetriever()],
    )
    manager = MemoryManager(
        stores=[
            MemoryStoreConfig(
                name="default",
                description="Default memory store.",
                store=store,
            )
        ],
        extractor=extractor,
    )
    return GenericMemoryAdapter(manager), store


def test_generic_adapter_extracts_provider_messages() -> None:
    extractor = RecordingExtractor()
    adapter, store = build_adapter(extractor)

    result = adapter.extract(
        messages=[
            {"role": "user", "content": "I prefer concise answers."},
            {"role": "assistant", "content": "I will keep it short."},
        ],
        namespace=("user", "default"),
        thread_id="thread-1",
    )

    assert len(result.records) == 1
    assert store.get(("user", "default"), "answer_style") is not None
    assert extractor.requests[0].conversation.thread_id == "thread-1"
    assert [message.role for message in extractor.requests[0].conversation.messages] == [
        "user",
        "assistant",
    ]


def test_generic_adapter_returns_injected_context_message() -> None:
    adapter, store = build_adapter()
    store.put(
        KnowledgeMemory(
            id="timezone",
            namespace=("user", "default"),
            key="timezone",
            content="User works in the Africa/Nairobi timezone.",
        )
    )

    message = adapter.inject_message(
        query="timezone",
        namespace=("user", "default"),
    )

    assert message == {
        "role": "system",
        "content": "\n".join(
            [
                "Relevant memory:",
                "",
                "Known facts:",
                "- User works in the Africa/Nairobi timezone.",
            ]
        ),
    }


def test_generic_adapter_returns_none_when_no_context_exists() -> None:
    adapter, _store = build_adapter()

    assert (
        adapter.inject_message(
            query="unknown",
            namespace=("user", "default"),
        )
        is None
    )


def test_generic_adapter_can_validate_messages_strictly() -> None:
    adapter, _store = build_adapter()

    with pytest.raises(ValueError, match="missing role"):
        adapter.extract(
            messages=[{"content": "No role."}],
            namespace=("user", "default"),
            thread_id="thread-1",
            strict_messages=True,
        )
