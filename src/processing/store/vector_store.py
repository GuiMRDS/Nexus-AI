"""Armazenamento e busca vetorial com ChromaDB."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from processing.store.embeddings import EmbeddingService


@dataclass(slots=True)
class VectorSearchResult:
    """Representa um resultado da busca vetorial."""

    id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None = None


def _json_scalar(value: Any) -> str | int | float | bool:
    """Converte valores de metadados para tipos aceitos pelo ChromaDB."""
    if value is None:
        return ""

    if isinstance(value, (str, int, float, bool)):
        return value

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


class VectorStore:
    """Gerencia a persistência e a consulta dos embeddings."""

    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collection_name: str | None = None,
        embedding_service: EmbeddingService | None = None,
        collection: Any | None = None,
    ) -> None:
        self.persist_directory = Path(
            persist_directory
            or os.getenv(
                "NEXUS_VECTOR_STORE_DIR",
                "data/vector_store",
            )
        )

        self.collection_name = (
            collection_name
            or os.getenv(
                "NEXUS_VECTOR_COLLECTION",
                "nexus_documents",
            )
        )

        self.embedding_service = (
            embedding_service or EmbeddingService()
        )

        if collection is not None:
            self._collection = collection
            self._client = None
            return

        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "Instale a dependência chromadb."
            ) from exc

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self) -> Any:
        """Retorna a coleção do ChromaDB."""
        return self._collection

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        text = getattr(chunk, "text", None)

        if not isinstance(text, str):
            raise TypeError(
                "Cada chunk precisa ter o atributo text do tipo str."
            )

        return text

    @staticmethod
    def _chunk_metadata(chunk: Any) -> dict[str, Any]:
        metadata = getattr(chunk, "metadata", {}) or {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "O atributo metadata deve ser um dicionário."
            )

        return metadata

    @staticmethod
    def _stable_id(
        metadata: dict[str, Any],
        text: str,
        position: int,
    ) -> str:
        source = (
            metadata.get("source_path")
            or metadata.get("source_file")
            or metadata.get("source")
            or "unknown"
        )

        chunk_index = metadata.get("chunk_index", position)
        raw = f"{source}|{chunk_index}|{text}"

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def upsert_chunks(self, chunks: Iterable[Any]) -> int:
        """Gera embeddings e insere ou atualiza chunks."""
        chunk_list = list(chunks)

        if not chunk_list:
            return 0

        documents = [
            self._chunk_text(chunk)
            for chunk in chunk_list
        ]

        if any(not document.strip() for document in documents):
            raise ValueError(
                "Não é possível indexar chunks vazios."
            )

        metadatas = [
            {
                key: _json_scalar(value)
                for key, value in self._chunk_metadata(chunk).items()
            }
            for chunk in chunk_list
        ]

        ids = [
            self._stable_id(
                self._chunk_metadata(chunk),
                document,
                index,
            )
            for index, (chunk, document) in enumerate(
                zip(chunk_list, documents)
            )
        ]

        embeddings = self.embedding_service.encode_documents(
            documents
        )

        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return len(chunk_list)

    def delete_by_source_path(
        self,
        source_path: str | Path,
    ) -> None:
        """Remove os chunks associados a um arquivo."""
        path = str(Path(source_path))

        self._collection.delete(
            where={"source_path": path}
        )

    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Busca os chunks semanticamente mais próximos."""
        if limit < 1:
            raise ValueError(
                "'limit' deve ser maior ou igual a 1."
            )

        query_vector = self.embedding_service.encode_query(
            query
        )

        response = self._collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        ids = (response.get("ids") or [[]])[0]
        documents = (response.get("documents") or [[]])[0]
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]

        results = []

        for index, item_id in enumerate(ids):
            results.append(
                VectorSearchResult(
                    id=item_id,
                    text=(
                        documents[index]
                        if index < len(documents)
                        else ""
                    ),
                    metadata=(
                        metadatas[index]
                        if index < len(metadatas)
                        else {}
                    ),
                    distance=(
                        distances[index]
                        if index < len(distances)
                        else None
                    ),
                )
            )

        return results
