"""Sincroniza o índice vetorial com a pasta de documentos (criações, alterações e remoções)."""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from processing.store.sync import sync_directory
from processing.store.vector_store import VectorStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reindexa só os documentos novos ou alterados e remove do índice "
            "os documentos apagados."
        )
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default="data/documents",
        help="Diretório dos documentos.",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Não percorre subdiretórios.",
    )

    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Desativa OCR durante o processamento.",
    )

    parser.add_argument(
        "--intervalo",
        type=float,
        default=0,
        metavar="MINUTOS",
        help=(
            "Repete a sincronização a cada N minutos até ser interrompido. "
            "Sem esta opção, executa uma vez (ideal para cron/Agendador de Tarefas)."
        ),
    )

    args = parser.parse_args()
    store = VectorStore()

    while True:
        result = sync_directory(
            Path(args.directory),
            vector_store=store,
            recursive=not args.no_recursive,
            enable_ocr=not args.no_ocr,
        )
        result["executado_em"] = datetime.now().isoformat(timespec="seconds")
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

        if args.intervalo <= 0:
            return 0 if not result["errors"] else 1

        try:
            time.sleep(args.intervalo * 60)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
