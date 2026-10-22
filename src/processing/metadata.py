from __future__ import annotations

from pathlib import Path
from typing import Any


def build_document_metadata(
    path: str | Path,
    *,
    category: str = "geral",
    responsible: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gera metadados básicos sem inventar autor ou datas internas.

    `created_at` usa a data de criação reportada pelo sistema de arquivos, que
    pode não ser a data original do documento. Para preservar datas internas,
    passe-as explicitamente quando a fonte as disponibilizar.
    """
    file_path = Path(path)
    stat = file_path.stat()
    metadata: dict[str, Any] = {
        "source_file": file_path.name,
        "source_path": str(file_path.resolve()),
        "file_type": file_path.suffix.lower().lstrip("."),
        "category": category,
        "file_size_bytes": stat.st_size,
        "file_created_at": created_at or _timestamp(stat.st_ctime),
        "file_modified_at": updated_at or _timestamp(stat.st_mtime),
        "responsible": responsible,
    }
    if extra:
        metadata.update(extra)
    return metadata


def _timestamp(value: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()