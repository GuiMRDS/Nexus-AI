"""Compara modelos da Groq no conjunto de avaliação antes de trocar o modelo em produção.

O primeiro modelo informado é a referência (normalmente o atual de produção).
Requer GROQ_API_KEY e o índice vetorial já criado.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from maintenance.avaliacao import (
    DEFAULT_DATASET,
    avaliar_modelo,
    candidato_aprovado,
    carregar_casos,
)
from nexus_ai.config import get_groq_model


def _pct(value):
    return "—" if value is None else f"{value:.0%}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Avalia e compara modelos do agente.")
    parser.add_argument(
        "--modelos",
        nargs="+",
        default=None,
        help="Modelos a comparar; o primeiro é a referência (padrão: GROQ_MODEL atual).",
    )
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Arquivo JSONL de perguntas.")
    parser.add_argument(
        "--saida",
        default="data/avaliacao/resultados",
        help="Pasta onde o relatório JSON completo é salvo.",
    )
    args = parser.parse_args()

    modelos = args.modelos or [get_groq_model()]
    casos = carregar_casos(args.dataset)
    relatorios = []

    for modelo in modelos:
        print(f"Avaliando {modelo} ({len(casos)} perguntas)...", flush=True)
        relatorio = avaliar_modelo(modelo, casos)
        relatorios.append(relatorio)
        for caso in relatorio["casos"]:
            if not caso["cobertura_ok"] or caso["conteudo_ok"] is False:
                detalhe = caso["erro"] or (
                    f"faltou {caso['faltando']}" if caso["faltando"] else
                    ("respondeu fora do escopo" if caso["respondeu"] else "não respondeu")
                )
                print(f"   x {caso['pergunta']} — {detalhe}")

    print(f"\n{'Modelo':<40} {'Cobertura':>10} {'Conteúdo':>9} {'Fora esc.':>9} {'Erros':>6} {'Latência':>9}")
    for relatorio in relatorios:
        resumo = relatorio["resumo"]
        latencia = resumo["latencia_media_ms"]
        print(
            f"{relatorio['modelo']:<40} {_pct(resumo['cobertura']):>10} {_pct(resumo['conteudo']):>9}"
            f" {resumo['falsos_positivos']:>9} {resumo['erros']:>6}"
            f" {(str(latencia) + ' ms') if latencia is not None else '—':>9}"
        )

    base = relatorios[0]
    for candidato in relatorios[1:]:
        aprovado = candidato_aprovado(base["resumo"], candidato["resumo"])
        veredito = "pode substituir" if aprovado else "manter o modelo atual"
        print(f"\n{candidato['modelo']} vs {base['modelo']}: {veredito}.")

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    arquivo = saida / f"avaliacao_{datetime.now():%Y%m%d_%H%M%S}.json"
    arquivo.write_text(json.dumps(relatorios, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRelatório completo: {arquivo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
