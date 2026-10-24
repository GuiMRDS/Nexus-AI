from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from processing.models import DocumentChunk


def save_chunks_jsonl(
    chunks: Iterable[DocumentChunk],
    destination: str | Path,
) -> Path:
    """Salva chunks em JSON Lines, um objeto JSON por linha.

    Este armazenamento local é útil para inspecionar o processamento.
    Não é um banco vetorial e ainda não implementa recuperação RAG.
    """
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            record = {"text": chunk.text, "metadata": chunk.metadata}
            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    return output_path


def load_chunks_jsonl(source: str | Path) -> list[DocumentChunk]:
    """Carrega chunks previamente salvos em JSON Lines."""
    input_path = Path(source)
    if not input_path.is_file():
        raise FileNotFoundError(f"Arquivo de chunks não encontrado: {input_path}")

    chunks: list[DocumentChunk] = []
    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                chunks.append(
                    DocumentChunk(
                        text=str(record["text"]),
                        metadata=dict(record.get("metadata", {})),
                    )
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Registro inválido no arquivo {input_path}, linha {line_number}."
                ) from exc

    return chunks