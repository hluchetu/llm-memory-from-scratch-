from __future__ import annotations

DEFAULT_SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_SENTENCE_TRANSFORMER_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        embedding = self._model.encode(text, normalize_embeddings=True)
        return [float(value) for value in embedding]
