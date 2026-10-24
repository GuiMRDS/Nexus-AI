from functools import lru_cache
from uuid import uuid4

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from agents.document_search import buscar_documentacao, montar_contexto_documental
from nexus_ai.config import get_groq_api_key
from my_models import GROQ_MODEL
from nexus_ai.schemas import AgentResponse


@lru_cache(maxsize=1)
def get_agent():
    """Cria o agente uma única vez por processo."""
    model = ChatGroq(
        model=GROQ_MODEL,
        api_key=get_groq_api_key(),
        temperature=0,
    )

    return create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        response_format=AgentResponse,
        system_prompt=(
            "Você é o assistente de atendimento do SaaS Nexus_IA. Responda sempre em português brasileiro. "
            "Sua prioridade é responder perguntas sobre planos, preços, limites, produto, funcionalidades, "
            "suporte, privacidade, termos e demais assuntos descritos na documentação fornecida. "
            "Use os trechos de documentação enviados junto com a pergunta como fonte principal. "
            "Responda de forma direta e útil, preservando valores, limites, prazos e condições exatamente "
            "como aparecem nos documentos. Não invente políticas, funcionalidades, preços ou garantias. "
            "Se os trechos não contiverem a resposta, diga claramente que não encontrou essa informação "
            "na documentação disponível e, quando útil, explique o que está documentado. "
            "Não apresente como fato informações que não estejam sustentadas pelos trechos. "
            "Os documentos podem ser demonstrativos/fictícios; informe isso quando for relevante. "
            "O campo fontes deve conter os caminhos dos arquivos fornecidos no contexto que sustentam a resposta."
        ),
    )


def executar_agente(pergunta: str) -> AgentResponse:
    """Busca primeiro nos documentos locais e entrega os trechos encontrados ao modelo."""
    passages = buscar_documentacao(pergunta)
    context = montar_contexto_documental(passages)
    source_paths = list(dict.fromkeys(passage.source for passage in passages))

    user_message = (
        f"PERGUNTA DO USUÁRIO:\n{pergunta}\n\n"
        f"TRECHOS RECUPERADOS DA DOCUMENTAÇÃO LOCAL:\n{context}\n\n"
        "Responda à pergunta usando os trechos acima. Se não houver informação suficiente, diga isso."
    )

    result = get_agent().invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": str(uuid4())}},
    )
    structured_response = result.get("structured_response")
    if structured_response is None:
        raise RuntimeError("O agente não retornou uma resposta estruturada.")
    if not isinstance(structured_response, AgentResponse):
        structured_response = AgentResponse.model_validate(structured_response)

    # As fontes são determinadas pelo código a partir dos arquivos realmente consultados,
    # em vez de depender de o modelo inventar ou esquecer os caminhos.
    return structured_response.model_copy(update={"fontes": source_paths, "usou_rag": False})


def main() -> None:
    """Teste rápido do agente."""
    pergunta = "Quais são os limites do plano Gratuito?"
    resposta = executar_agente(pergunta)
    print(resposta.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()