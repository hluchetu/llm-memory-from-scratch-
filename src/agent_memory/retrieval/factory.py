from __future__ import annotations

from agent_memory.embeddings import SentenceTransformerEmbedder
from agent_memory.long_term import MemoryStore
from agent_memory.long_term import MemoryStorage
from agent_memory.long_term import SQLiteMemoryStorage
from agent_memory.retrieval.episodic import EpisodicMemoryRetriever
from agent_memory.retrieval.hybrid import HybridMemoryRetriever
from agent_memory.retrieval.lexical import LexicalMemoryRetriever
from agent_memory.retrieval.procedural import ProceduralMemoryRetriever
from agent_memory.retrieval.semantic import SemanticMemoryRetriever
from agent_memory.settings import Settings
from agent_memory.settings import get_settings
from agent_memory.vector_store import ChromaVectorStore
from agent_memory.vector_store import VectorStore


def create_memory_store(
    settings: Settings | None = None,
    storage: MemoryStorage | None = None,
    vector_store: VectorStore | None = None,
) -> MemoryStore:
    resolved_settings = settings or get_settings()
    resolved_storage = storage or SQLiteMemoryStorage(
        resolved_settings.long_term_database_path
    )

    return MemoryStore(
        storage=resolved_storage,
        retrievers=[
            _create_memory_retriever(resolved_settings, resolved_storage, vector_store),
        ],
    )


def _create_memory_retriever(
    settings: Settings,
    storage: MemoryStorage,
    vector_store: VectorStore | None = None,
) -> HybridMemoryRetriever:
    lexical = LexicalMemoryRetriever()
    episodic = EpisodicMemoryRetriever()
    procedural = ProceduralMemoryRetriever()

    if not settings.semantic_retrieval_enabled:
        return HybridMemoryRetriever(
            retrievers=[
                lexical,
                episodic,
                procedural,
            ],
            routes={
                "semantic": [lexical],
                "entity": [lexical],
                "episodic": [episodic, lexical],
                "procedural": [procedural, lexical],
                "preference": [lexical],
                "decision": [episodic, lexical],
                None: [lexical, episodic, procedural],
            },
        )

    resolved_vector_store = vector_store or ChromaVectorStore(
        path=settings.vector_store_path or settings.memory_directory / "chroma",
        collection_name=settings.vector_store_collection,
    )

    semantic = SemanticMemoryRetriever(
        embedder=SentenceTransformerEmbedder(model_name=settings.embedding_model),
        vector_store=resolved_vector_store,
        storage=storage,
    )

    return HybridMemoryRetriever(
        retrievers=[
            lexical,
            semantic,
            episodic,
            procedural,
        ],
        routes={
            "semantic": [semantic, lexical],
            "entity": [semantic, lexical],
            "episodic": [episodic, lexical],
            "procedural": [procedural, lexical],
            "preference": [semantic, lexical],
            "decision": [episodic, lexical],
            None: [semantic, lexical, episodic, procedural],
        },
    )
