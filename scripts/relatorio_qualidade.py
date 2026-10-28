"""Relatório de qualidade a partir das interações registradas pela API."""

import argparse
import json

from nexus_ai.monitoring import MonitoringStore


def _pct(value):
    return "—" if value is None else f"{value:.0%}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mostra taxa de perguntas sem resposta, feedback negativo e tempo de resposta."
    )
    parser.add_argument("--dias", type=int, default=30, help="Período analisado (padrão: 30).")
    parser.add_argument("--json", action="store_true", help="Imprime as métricas em JSON.")
    args = parser.parse_args()

    metricas = MonitoringStore().metricas(dias=args.dias)
    if args.json:
        print(json.dumps(metricas, ensure_ascii=False, indent=2))
        return 0

    feedback = metricas["feedback"]
    print(f"Últimos {metricas['periodo_dias']} dias")
    print(f"  Perguntas:            {metricas['total_perguntas']} ({metricas['erros']} com erro)")
    print(f"  Sem resposta:         {metricas['sem_resposta']} ({_pct(metricas['taxa_sem_resposta'])})")
    print(f"  Feedback:             {feedback['positivo']} positivos, {feedback['negativo']} negativos"
          f" ({_pct(feedback['taxa_negativa'])} negativo)")
    print(f"  Tempo de resposta:    média {metricas['latencia_media_ms'] or '—'} ms,"
          f" p95 {metricas['latencia_p95_ms'] or '—'} ms")

    if metricas["perguntas_sem_resposta"]:
        print("\nPerguntas recorrentes sem resposta (possíveis lacunas na base):")
        for item in metricas["perguntas_sem_resposta"]:
            print(f"  {item['ocorrencias']:>3}×  {item['pergunta']}")

    if metricas["respostas_mal_avaliadas"]:
        print("\nRespostas avaliadas negativamente (revisar prompt/recuperação):")
        for item in metricas["respostas_mal_avaliadas"]:
            motivo = f" — {item['motivo']}" if item["motivo"] else ""
            print(f"  • {item['pergunta']}{motivo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
