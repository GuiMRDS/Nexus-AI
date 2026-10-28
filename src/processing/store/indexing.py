"""Funções de alto nível para indexação de documentos."""

from pathlib import Path
from typing import Any

from processing.pipeline import processar_documento
from processing.extractors import SUPPORTED_EXTENSIONS
from processing.store.vector_store import VectorStore


def index_document(
    path: str | Path,
    vector_store: VectorStore | None = None,
    category: str | None = None,
    responsible: str | None = None,
    enable_ocr: bool = True,
) -> int:
    """Processa e indexa um documento e retorna a quantidade de chunks."""
    file_path = Path(path).expanduser().resolve()

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Documento não encontrado: {file_path}"
        )

    store = vector_store or VectorStore()

    chunks = processar_documento(
        file_path,
        category=category or "geral",
        responsible=responsible,
        enable_ocr=enable_ocr,
    )

    for index, chunk in enumerate(chunks):
        chunk.metadata.setdefault(
            "source_path",
            str(file_path),
        )
        chunk.metadata.setdefault(
            "source_file",
            file_path.name,
        )
        chunk.metadata.setdefault(
            "chunk_index",
            index,
        )

    # Remove a versão anterior do arquivo para não deixar trechos desatualizados.
    store.delete_by_source_path(file_path)
    return store.upsert_chunks(chunks)


def category_from_path(path: str | Path, root: str | Path) -> str:
    """Usa a primeira subpasta abaixo de `root` como categoria (ex.: suporte).

    Arquivos diretamente na raiz ficam na categoria "geral".
    """
    relative = Path(path).relative_to(Path(root))
    return relative.parts[0].lower() if len(relative.parts) > 1 else "geral"


def index_directory(
    directory: str | Path,
    vector_store: VectorStore | None = None,
    recursive: bool = True,
    enable_ocr: bool = True,
) -> dict[str, Any]:
    """Indexa os documentos suportados de um diretório."""
    root = Path(directory).expanduser().resolve()

    if not root.is_dir():
        raise NotADirectoryError(
            f"Diretório não encontrado: {root}"
        )

    store = vector_store or VectorStore()

    extensions = {
        str(extension).lower()
        for extension in SUPPORTED_EXTENSIONS
    }

    paths = root.rglob("*") if recursive else root.glob("*")

    summary: dict[str, Any] = {
        "directory": str(root),
        "files_found": 0,
        "files_indexed": 0,
        "chunks_indexed": 0,
        "errors": [],
    }

    for path in sorted(paths):
        if not path.is_file():
            continue

        if path.suffix.lower() not in extensions:
            continue

        summary["files_found"] += 1

        try:
            count = index_document(
                path,
                vector_store=store,
                category=category_from_path(path, root),
                enable_ocr=enable_ocr,
            )

            summary["files_indexed"] += 1
            summary["chunks_indexed"] += count

        except Exception as exc:
            summary["errors"].append({
                "file": str(path),
                "error": str(exc),
            })

    return summary
