"""Relatório de curadoria: documentos que cada responsável precisa revisar."""

import argparse
import json
from collections import defaultdict

from maintenance.curadoria import relatorio_curadoria


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lista documentos com revisão vencida, em rascunho ou alterados após a revisão."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Diretório dos documentos (padrão: data/documents).",
    )
    parser.add_argument(
        "--prazo-dias",
        type=int,
        default=None,
        help="Dias desde a última revisão para considerá-la vencida (padrão: 90).",
    )
    parser.add_argument("--json", action="store_true", help="Imprime o relatório em JSON.")
    args = parser.parse_args()

    relatorio = relatorio_curadoria(args.directory, prazo_dias=args.prazo_dias)

    if args.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        por_responsavel = defaultdict(list)
        for pendencia in relatorio["pendencias"]:
            por_responsavel[pendencia["responsavel"]].append(pendencia)

        print(f"Curadoria em {relatorio['gerado_em']} (prazo de revisão: {relatorio['prazo_dias']} dias)")
        print(f"Documentos inventariados: {relatorio['documentos_inventariados']}\n")
        for responsavel, pendencias in sorted(por_responsavel.items()):
            print(f"## {responsavel}")
            for pendencia in pendencias:
                print(f"- {pendencia['documento']} {pendencia['nome']}")
                for motivo in pendencia["motivos"]:
                    print(f"    · {motivo}")
            print()
        if relatorio["arquivos_sem_inventario"]:
            print("## Arquivos indexáveis sem registro no inventário")
            for nome in relatorio["arquivos_sem_inventario"]:
                print(f"- {nome}")
        if not relatorio["pendencias"] and not relatorio["arquivos_sem_inventario"]:
            print("Nenhuma pendência de curadoria.")

    return 1 if relatorio["pendencias"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
