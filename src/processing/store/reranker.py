"""Reranqueamento de candidatos recuperados pela busca vetorial."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


class Reranker:
    """Reavalia candidatos com um cross-encoder, mais lento porém mais preciso.

    Ao contrário do modelo de embeddings (que codifica pergunta e trecho
    separadamente), o cross-encoder recebe os dois juntos e produz uma única
    pontuação de relevância, o que custa mais caro por candidato e por isso só
    é aplicado sobre o conjunto reduzido devolvido pela busca vetorial.
    """

    def __init__(self, model_name: str | None = None, model: Any | None = None) -> None:
        self.model_name = (
            model_name or os.getenv("NEXUS_RERANKER_MODEL") or DEFAULT_MODEL_NAME
        )
        self._model = model

    def _get_model(self) -> Any:
        """Carrega o modelo somente quando necessário."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "Instale a dependência sentence-transformers."
                ) from exc

            self._model = CrossEncoder(self.model_name)

        return self._model

    def score(self, query: str, passages: list[str]) -> list[float]:
        """Pontua cada trecho de acordo com a relevância real para a pergunta."""
        if not passages:
            return []

        model = self._get_model()
        pairs = [(query, passage) for passage in passages]
        scores = model.predict(pairs)

        # Aceita tanto arrays NumPy quanto listas Python.
        if hasattr(scores, "tolist"):
            scores = scores.tolist()

        return [float(score) for score in scores]
