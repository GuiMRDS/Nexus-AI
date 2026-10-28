"""Sincronização incremental entre a pasta de documentos e o índice vetorial.

Um manifesto JSON guarda o hash de cada arquivo indexado. A cada execução:
- arquivos novos ou com conteúdo alterado são reprocessados e reindexados;
- arquivos que sumiram da pasta têm seus trechos removidos do índice;
- arquivos sem mudança são ignorados (nenhum embedding é recalculado).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from processing.extractors import SUPPORTED_EXTENSIONS
from processing.store.indexing import category_from_path, index_document
from processing.store.vector_store import VectorStore

MANIFEST_FILE = "manifest.json"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("files", {})
    except (OSError, ValueError):
        return {}


def _save_manifest(path: Path, files: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"files": files}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(path)


def sync_directory(
    directory: str | Path,
    vector_store: VectorStore | None = None,
    *,
    manifest_path: str | Path | None = None,
    recursive: bool = True,
    enable_ocr: bool = True,
    indexer: Callable[..., int] = index_document,
) -> dict[str, Any]:
    """Aplica ao índice as criações, alterações e remoções de documentos."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Diretório não encontrado: {root}")

    store = vector_store or VectorStore()
    manifest_file = Path(manifest_path or Path(store.persist_directory) / MANIFEST_FILE)
    previous = _load_manifest(manifest_file)
    current: dict[str, dict[str, Any]] = {}

    extensions = {str(extension).lower() for extension in SUPPORTED_EXTENSIONS}
    paths = root.rglob("*") if recursive else root.glob("*")

    summary: dict[str, Any] = {
        "directory": str(root),
        "added": [],
        "updated": [],
        "removed": [],
        "unchanged": 0,
        "chunks_indexed": 0,
        "errors": [],
    }

    for path in sorted(paths):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue

        key = str(path.resolve())
        digest = file_hash(path)
        known = previous.get(key)
        if known and known.get("hash") == digest:
            current[key] = known
            summary["unchanged"] += 1
            continue

        category = category_from_path(path, root)
        try:
            count = indexer(path, vector_store=store, category=category, enable_ocr=enable_ocr)
        except Exception as exc:
            # Mantém a entrada antiga: na próxima execução o arquivo é tentado de novo.
            if known:
                current[key] = known
            summary["errors"].append({"file": key, "error": str(exc)})
            continue

        current[key] = {
            "hash": digest,
            "category": category,
            "chunks": count,
            "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        summary["updated" if known else "added"].append(key)
        summary["chunks_indexed"] += count

    for key in sorted(set(previous) - set(current)):
        # Entradas de outras pastas sincronizadas com o mesmo manifesto ficam intactas.
        out_of_scope = not Path(key).is_relative_to(root) or (
            not recursive and Path(key).parent != root
        )
        if out_of_scope:
            current[key] = previous[key]
            continue
        try:
            store.delete_by_source_path(key)
        except Exception as exc:
            current[key] = previous[key]
            summary["errors"].append({"file": key, "error": str(exc)})
            continue
        summary["removed"].append(key)

    _save_manifest(manifest_file, current)
    return summary
