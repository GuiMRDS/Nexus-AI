"""Camada de recuperação (RAG): busca semântica, filtragem, reranqueamento e contexto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from processing.store.reranker import Reranker
from processing.store.vector_store import VectorStore


@dataclass(slots=True)
class RetrievedPassage:
    """Trecho recuperado, com as pontuações de cada etapa da recuperação."""

    text: str
    metadata: dict[str, Any]
    vector_distance: float | None
    rerank_score: float | None = None

    @property
    def source(self) -> str:
        return str(
            self.metadata.get("source_file")
            or self.metadata.get("source_path")
            or "desconhecido"
        )

    @property
    def section(self) -> str:
        return str(self.metadata.get("section_title") or "Geral")


class Retriever:
    """Recupera e reordena os trechos mais relevantes para uma pergunta.

    1. A pergunta é transformada em embedding pelo mesmo modelo usado na
       indexação (feito dentro do `VectorStore`/`EmbeddingService`).
    2. O banco vetorial devolve os `candidate_limit` trechos mais próximos
       semanticamente, já aplicando o filtro de metadados recebido em `where`.
    3. Os candidatos passam por um cross-encoder (`Reranker`), que avalia a
       pergunta completa junto de cada trecho e produz uma pontuação de
       relevância mais precisa que a distância vetorial isolada.
    4. Os `limit` trechos mais bem pontuados são devolvidos, já prontos para
       virar o contexto do prompt enviado ao LLM.
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.reranker = reranker or Reranker()

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        candidate_limit: int = 20,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedPassage]:
        """Busca semântica com filtragem por metadados e reranqueamento."""
        if candidate_limit < limit:
            raise ValueError(
                "'candidate_limit' deve ser maior ou igual a 'limit'."
            )

        candidates = self.vector_store.search(
            query,
            limit=candidate_limit,
            where=where,
        )
        if not candidates:
            return []

        scores = self.reranker.score(
            query,
            [candidate.text for candidate in candidates],
        )

        passages = [
            RetrievedPassage(
                text=candidate.text,
                metadata=candidate.metadata,
                vector_distance=candidate.distance,
                rerank_score=score,
            )
            for candidate, score in zip(candidates, scores)
        ]

        passages.sort(key=lambda passage: passage.rerank_score, reverse=True)
        return passages[:limit]


def montar_contexto_vetorial(passages: list[RetrievedPassage]) -> str:
    """Monta o bloco de contexto com as fontes, para o prompt enviado ao LLM."""
    if not passages:
        return "Nenhum trecho relevante foi encontrado na documentação indexada."

    blocks = []
    for index, passage in enumerate(passages, start=1):
        header = f"[Documento {index}]\nArquivo: {passage.source}\nSeção: {passage.section}"
        updated_at = passage.metadata.get("file_modified_at")
        if updated_at:
            header += f"\nAtualizado em: {updated_at}"
        blocks.append(f"{header}\nConteúdo:\n{passage.text}")

    return "\n\n---\n\n".join(blocks)
