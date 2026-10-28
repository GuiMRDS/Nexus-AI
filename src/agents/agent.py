from functools import lru_cache
from uuid import uuid4

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from agents.contacts import carregar_contatos
from agents.validation import RespostaGerada, filtrar_por_relevancia, validar_resposta
from nexus_ai.config import get_groq_api_key, get_groq_model, get_min_relevance
from nexus_ai.schemas import AgentResponse, Fonte, Turno
from processing.retrieval import RetrievedPassage, Retriever, montar_contexto_vetorial

RESPOSTA_NAO_ENCONTRADA = "Não encontrei essa informação nos documentos disponíveis."


@lru_cache(maxsize=1)
def get_agent():
    """Cria o agente uma única vez por processo."""
    model = ChatGroq(
        model=get_groq_model(),
        api_key=get_groq_api_key(),
        temperature=0,
    )

    return create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        response_format=RespostaGerada,
        system_prompt=(
            "Você é o assistente de atendimento do SaaS Nexus_IA. Responda sempre em português brasileiro. "
            "Responda SOMENTE com base nos trechos de documentação enviados junto com a pergunta. "
            "Não use conhecimento externo, não deduza políticas e não invente funcionalidades, "
            "preços, prazos ou garantias. Preserve valores, limites, prazos e condições exatamente "
            "como aparecem nos trechos. "
            "Cada trecho vem identificado como [Documento N]. Em documentos_citados, informe os "
            "números N de todos os trechos que sustentam a resposta. "
            "Se os trechos não contiverem a informação pedida, defina encontrou_resposta como false "
            "e não tente responder. Se cobrirem só parte da pergunta, responda apenas essa parte "
            "e deixe claro o que não está documentado. "
            "Escreva um resumo direto e útil; não liste as fontes no texto, pois elas são anexadas "
            "automaticamente. "
            "Se houver conversa anterior, use-a só para entender a que a pergunta se refere; "
            "ela nunca é fonte de informação. "
            "Os documentos podem ser demonstrativos/fictícios; informe isso quando for relevante."
        ),
    )


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    """Carrega os modelos de embeddings e reranqueamento uma única vez."""
    return Retriever()


def _fonte(passage: RetrievedPassage) -> Fonte:
    return Fonte(
        arquivo=passage.source,
        secao=passage.metadata.get("section_title") or None,
        localizacao=passage.location,
        area=passage.category,
        atualizado_em=passage.updated_at,
    )


def resposta_sem_informacao() -> AgentResponse:
    """Fallback: informa a ausência da informação e indica as áreas responsáveis."""
    linhas = [
        RESPOSTA_NAO_ENCONTRADA,
        "A pergunta pode estar fora do escopo da base de conhecimento do Nexus_IA.",
    ]
    contatos = carregar_contatos()
    if contatos:
        linhas.append("Se precisar, fale com a área responsável:")
        linhas.extend(
            f"- {contato.area}: {contato.contato} ({contato.assuntos})"
            for contato in contatos
        )
    return AgentResponse(
        resposta="\n".join(linhas),
        fontes=[],
        usou_rag=False,
        encontrou_resposta=False,
    )


def _conversa_anterior(historico: list[Turno]) -> str:
    return "\n".join(
        f"Usuário: {turno.pergunta}\nAssistente: {turno.resposta}" for turno in historico
    )


def _gerar(
    pergunta: str,
    contexto: str,
    problemas: list[str] | None = None,
    historico: list[Turno] | None = None,
) -> RespostaGerada:
    user_message = ""
    if historico:
        user_message += (
            "CONVERSA ANTERIOR (apenas para entender a pergunta, não é fonte):\n"
            f"{_conversa_anterior(historico)}\n\n"
        )
    user_message += (
        f"PERGUNTA DO USUÁRIO:\n{pergunta}\n\n"
        f"TRECHOS RECUPERADOS DA DOCUMENTAÇÃO:\n{contexto}\n\n"
        "Responda à pergunta usando somente os trechos acima."
    )
    if problemas:
        user_message += (
            "\n\nSUA RESPOSTA ANTERIOR FOI REJEITADA NA VALIDAÇÃO:\n- "
            + "\n- ".join(problemas)
            + "\nGere uma nova resposta corrigindo esses problemas. Se os trechos não "
            "sustentarem a resposta, defina encontrou_resposta como false."
        )

    result = get_agent().invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": str(uuid4())}},
    )
    structured_response = result.get("structured_response")
    if structured_response is None:
        raise RuntimeError("O agente não retornou uma resposta estruturada.")
    if not isinstance(structured_response, RespostaGerada):
        structured_response = RespostaGerada.model_validate(structured_response)
    return structured_response


def _recuperar(pergunta: str, historico: list[Turno]) -> list[RetrievedPassage]:
    """Busca pela pergunta; se nada for relevante, tenta junto da pergunta anterior.

    Perguntas de continuação ("e no plano Pro?") quase não têm conteúdo sozinhas.
    A segunda busca só acontece quando a primeira falha, para não puxar o assunto
    antigo quando o usuário muda de tema.
    """
    min_score = get_min_relevance()
    passages = get_retriever().retrieve(pergunta, limit=5, candidate_limit=20)
    relevantes = filtrar_por_relevancia(passages, min_score)
    if relevantes or not historico:
        return relevantes

    consulta = f"{historico[-1].pergunta} {pergunta}"
    passages = get_retriever().retrieve(consulta, limit=5, candidate_limit=20)
    return filtrar_por_relevancia(passages, min_score)


def executar_agente(pergunta: str, historico: list[Turno] | None = None) -> AgentResponse:
    """Recupera os trechos relevantes, gera a resposta e valida o respaldo nos documentos."""
    historico = historico or []
    relevantes = _recuperar(pergunta, historico)
    # Sem trecho relevante o suficiente, nem chama o LLM: evita respostas sem base.
    if not relevantes:
        return resposta_sem_informacao()

    contexto = montar_contexto_vetorial(relevantes)
    gerada = _gerar(pergunta, contexto, historico=historico)
    problemas = validar_resposta(gerada, relevantes, pergunta)
    if problemas:
        gerada = _gerar(pergunta, contexto, problemas, historico)
        problemas = validar_resposta(gerada, relevantes, pergunta)

    if problemas or not gerada.encontrou_resposta:
        return resposta_sem_informacao()

    # As fontes vêm dos metadados reais dos trechos citados, não do texto do modelo.
    fontes: list[Fonte] = []
    for numero in dict.fromkeys(gerada.documentos_citados):
        fonte = _fonte(relevantes[numero - 1])
        if fonte not in fontes:
            fontes.append(fonte)
    return AgentResponse(
        resposta=gerada.resposta,
        fontes=fontes,
        usou_rag=True,
        encontrou_resposta=True,
    )


def main() -> None:
    """Teste rápido do agente."""
    pergunta = "Quais são os limites do plano Gratuito?"
    resposta = executar_agente(pergunta)
    print(resposta.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
