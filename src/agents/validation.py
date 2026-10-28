"""Controle de alucinação: limiar de relevância e verificação de consistência."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from processing.retrieval import RetrievedPassage

# Referências como "[Documento 2]" não são valores do conteúdo e não devem ser checadas.
_DOCUMENT_REF = re.compile(r"\[?\bdocumentos?\s+\d+(?:\s*(?:,|e)\s*\d+)*\]?", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


class RespostaGerada(BaseModel):
    """Saída estruturada pedida ao LLM, antes da validação."""

    resposta: str = Field(
        description="Resposta direta à pergunta, usando somente os trechos fornecidos."
    )
    encontrou_resposta: bool = Field(
        description="true se os trechos contêm a informação pedida; false caso contrário."
    )
    documentos_citados: list[int] = Field(
        default_factory=list,
        description="Números dos [Documento N] que sustentam a resposta.",
    )


def filtrar_por_relevancia(
    passages: list[RetrievedPassage],
    min_score: float,
) -> list[RetrievedPassage]:
    """Descarta trechos cujo score do reranker está abaixo do limiar."""
    return [
        passage
        for passage in passages
        if passage.rerank_score is not None and passage.rerank_score >= min_score
    ]


def _normalizar_numero(value: str) -> str:
    """Trata "79,90", "79.90" e "1.000" de forma equivalente."""
    digits = re.sub(r"[.,]", "", value)
    return digits.lstrip("0") or "0"


def _numeros(text: str) -> set[str]:
    return {_normalizar_numero(match) for match in _NUMBER.findall(text)}


def validar_resposta(
    gerada: RespostaGerada,
    passages: list[RetrievedPassage],
    pergunta: str = "",
) -> list[str]:
    """Verifica se a resposta tem respaldo nos trechos. Devolve a lista de problemas.

    Checagens determinísticas (sem uma segunda chamada ao LLM):
    - toda resposta afirmativa precisa citar ao menos um documento existente;
    - todo número da resposta (preços, limites, prazos, datas) precisa aparecer
      nos documentos citados ou na própria pergunta.
    """
    if not gerada.encontrou_resposta:
        return []

    problemas: list[str] = []
    invalidos = [n for n in gerada.documentos_citados if not 1 <= n <= len(passages)]
    if invalidos:
        problemas.append(
            f"Documentos citados inexistentes: {invalidos}. "
            f"Use apenas números entre 1 e {len(passages)}."
        )

    citados = [passages[n - 1] for n in gerada.documentos_citados if 1 <= n <= len(passages)]
    if not citados:
        problemas.append("A resposta não cita nenhum documento que a sustente.")
        return problemas

    numeros_resposta = _numeros(_DOCUMENT_REF.sub(" ", gerada.resposta))
    numeros_permitidos = _numeros(pergunta)
    for passage in citados:
        numeros_permitidos |= _numeros(passage.text)
    sem_respaldo = sorted(numeros_resposta - numeros_permitidos)
    if sem_respaldo:
        problemas.append(
            "Valores sem respaldo nos documentos citados: "
            + ", ".join(sem_respaldo)
            + ". Use apenas valores que aparecem nos trechos."
        )
    return problemas
