"""Script de linha de comando para indexar documentos."""

import argparse
import json
from pathlib import Path

from processing.store.indexing import index_directory


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Indexa documentos no armazenamento vetorial do Nexus_IA."
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

    args = parser.parse_args()

    result = index_directory(
        Path(args.directory),
        recursive=not args.no_recursive,
        enable_ocr=not args.no_ocr,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
