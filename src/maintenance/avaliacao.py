"""Avaliação do agente com um conjunto fixo de perguntas.

Usada antes de trocar o modelo em produção: roda as mesmas perguntas com o modelo
atual e com o candidato e compara cobertura (respondeu quando devia e recusou
quando devia), conteúdo (valores esperados presentes) e tempo de resposta.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from nexus_ai.schemas import AgentResponse, Turno

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "avaliacao" / "perguntas.jsonl"

Executor = Callable[[str, list[Turno]], AgentResponse]


@dataclass(slots=True)
class Caso:
    pergunta: str
    deve_responder: bool
    esperado: list[str]
    historico: list[Turno]


@dataclass(slots=True)
class ResultadoCaso:
    pergunta: str
    deve_responder: bool
    respondeu: bool
    cobertura_ok: bool
    conteudo_ok: bool | None
    faltando: list[str]
    latencia_ms: int
    resposta: str
    fontes: list[str]
    erro: str | None = None


def carregar_casos(path: str | Path | None = None) -> list[Caso]:
    casos = []
    linhas = Path(path or DEFAULT_DATASET).read_text(encoding="utf-8").splitlines()
    for linha in linhas:
        if not linha.strip() or linha.lstrip().startswith("//"):
            continue
        item = json.loads(linha)
        casos.append(
            Caso(
                pergunta=item["pergunta"],
                deve_responder=bool(item.get("deve_responder", True)),
                esperado=list(item.get("esperado", [])),
                historico=[Turno(**turno) for turno in item.get("historico", [])],
            )
        )
    return casos


def _contem(resposta: str, esperado: str) -> bool:
    """Comparação sem caixa e aceitando vírgula ou ponto decimal (79,90 = 79.90)."""
    texto = resposta.casefold()
    alvo = esperado.casefold()
    return alvo in texto or alvo.replace(",", ".") in texto or alvo.replace(".", ",") in texto


def avaliar_caso(caso: Caso, executar: Executor) -> ResultadoCaso:
    inicio = time.perf_counter()
    try:
        response = executar(caso.pergunta, caso.historico)
    except Exception as exc:
        return ResultadoCaso(
            pergunta=caso.pergunta,
            deve_responder=caso.deve_responder,
            respondeu=False,
            cobertura_ok=False,
            conteudo_ok=False if caso.esperado else None,
            faltando=list(caso.esperado),
            latencia_ms=round((time.perf_counter() - inicio) * 1000),
            resposta="",
            fontes=[],
            erro=f"{type(exc).__name__}: {exc}",
        )

    latencia_ms = round((time.perf_counter() - inicio) * 1000)
    respondeu = response.encontrou_resposta
    faltando = [item for item in caso.esperado if not _contem(response.resposta, item)]
    conteudo_ok = (respondeu and not faltando) if caso.deve_responder and caso.esperado else None
    return ResultadoCaso(
        pergunta=caso.pergunta,
        deve_responder=caso.deve_responder,
        respondeu=respondeu,
        cobertura_ok=respondeu == caso.deve_responder,
        conteudo_ok=conteudo_ok,
        faltando=faltando if caso.deve_responder else [],
        latencia_ms=latencia_ms,
        resposta=response.resposta,
        fontes=[fonte.arquivo for fonte in response.fontes],
    )


def resumir(resultados: list[ResultadoCaso]) -> dict[str, Any]:
    total = len(resultados)
    com_conteudo = [r for r in resultados if r.conteudo_ok is not None]
    latencias = [r.latencia_ms for r in resultados if r.erro is None]
    return {
        "total": total,
        "cobertura": sum(r.cobertura_ok for r in resultados) / total if total else None,
        "conteudo": (
            sum(bool(r.conteudo_ok) for r in com_conteudo) / len(com_conteudo)
            if com_conteudo
            else None
        ),
        "falsos_positivos": sum(r.respondeu and not r.deve_responder for r in resultados),
        "erros": sum(r.erro is not None for r in resultados),
        "latencia_media_ms": round(sum(latencias) / len(latencias)) if latencias else None,
    }


def avaliar(casos: list[Caso], executar: Executor) -> dict[str, Any]:
    resultados = [avaliar_caso(caso, executar) for caso in casos]
    return {"resumo": resumir(resultados), "casos": [asdict(r) for r in resultados]}


@contextmanager
def usando_modelo(modelo: str) -> Iterator[None]:
    """Troca GROQ_MODEL temporariamente e recria o agente com o novo modelo."""
    from agents import agent as agent_module

    anterior = os.environ.get("GROQ_MODEL")
    os.environ["GROQ_MODEL"] = modelo
    agent_module.get_agent.cache_clear()
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop("GROQ_MODEL", None)
        else:
            os.environ["GROQ_MODEL"] = anterior
        agent_module.get_agent.cache_clear()


def avaliar_modelo(modelo: str, casos: list[Caso]) -> dict[str, Any]:
    from agents.agent import executar_agente

    with usando_modelo(modelo):
        return {"modelo": modelo, **avaliar(casos, executar_agente)}


def candidato_aprovado(base: dict[str, Any], candidato: dict[str, Any]) -> bool:
    """O candidato só substitui o modelo atual se não piorar cobertura, conteúdo
    nem a quantidade de respostas dadas a perguntas fora do escopo."""

    def valor(resumo: dict[str, Any], chave: str) -> float:
        return resumo[chave] if resumo[chave] is not None else 0.0

    return (
        valor(candidato, "cobertura") >= valor(base, "cobertura")
        and valor(candidato, "conteudo") >= valor(base, "conteudo")
        and candidato["falsos_positivos"] <= base["falsos_positivos"]
        and candidato["erros"] == 0
    )
