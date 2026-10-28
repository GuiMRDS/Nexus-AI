"""Formatação final da resposta conforme o canal (chat, e-mail, texto simples)."""

from __future__ import annotations

from nexus_ai.schemas import AgentResponse, Canal, Fonte


def descrever_fonte(fonte: Fonte) -> str:
    """Ex.: "02_faq_suporte.pdf — Atendimento · página 2 · atualizado em 2026-10-21"."""
    detalhes = [
        parte
        for parte in (
            fonte.secao,
            fonte.localizacao,
            f"atualizado em {fonte.atualizado_em}" if fonte.atualizado_em else None,
        )
        if parte
    ]
    return f"{fonte.arquivo} — {' · '.join(detalhes)}" if detalhes else fonte.arquivo


def formatar_resposta(response: AgentResponse, canal: Canal = "chat") -> str:
    """Resumo direto seguido das referências aos documentos usados."""
    resposta = response.resposta.strip()

    if canal == "chat":
        partes = [resposta]
        if response.fontes:
            referencias = "\n".join(
                f"{indice}. {descrever_fonte(fonte)}"
                for indice, fonte in enumerate(response.fontes, start=1)
            )
            partes.append(f"**Fontes**\n{referencias}")
        return "\n\n".join(partes)

    if canal == "email":
        partes = ["Olá,", resposta]
        if response.fontes:
            referencias = "\n".join(
                f"  {indice}. {descrever_fonte(fonte)}"
                for indice, fonte in enumerate(response.fontes, start=1)
            )
            partes.append(f"Referências consultadas:\n{referencias}")
        partes.append("Atenciosamente,\nAssistente Nexus_IA")
        return "\n\n".join(partes)

    # "texto": sem Markdown, para canais como Teams/Slack em modo texto simples.
    partes = [resposta]
    if response.fontes:
        referencias = "\n".join(f"- {descrever_fonte(fonte)}" for fonte in response.fontes)
        partes.append(f"Fontes:\n{referencias}")
    return "\n\n".join(partes)
