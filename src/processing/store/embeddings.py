"""Geração de embeddings para documentos e consultas do Nexus_IA."""

from __future__ import annotations

import os
from typing import Any


DEFAULT_MODEL_NAME = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


class EmbeddingService:
    """Carrega um modelo multilíngue e gera embeddings normalizados."""

    def __init__(
        self,
        model_name: str | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_name = (
            model_name
            or os.getenv("NEXUS_EMBEDDING_MODEL")
            or DEFAULT_MODEL_NAME
        )
        self._model = model

    def _get_model(self) -> Any:
        """Carrega o modelo somente quando necessário."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Instale a dependência sentence-transformers."
                ) from exc

            self._model = SentenceTransformer(self.model_name)

        return self._model

    
    def _encode(self, texts: list[str]) -> list[list[float]]:
        """Converte uma lista de textos em vetores numéricos."""
        if not texts:
            return []

        model = self._get_model()

        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        # Aceita tanto arrays NumPy quanto listas Python.
        if hasattr(vectors, "tolist"):
            vectors = vectors.tolist()

        return vectors


    def encode_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Gera embeddings para os chunks dos documentos."""
        return self._encode(texts)

    def encode_query(self, query: str) -> list[float]:
        """Gera o embedding de uma consulta."""
        query = query.strip()

        if not query:
            raise ValueError("A consulta não pode estar vazia.")

        return self._encode([query])[0]
