from functools import lru_cache
from uuid import uuid4

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from nexus_ai.config import get_groq_api_key
from nexus_ai.my_models import GROQ_MODEL
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
            "Responda sempre em português brasileiro. "
            "Não invente fontes ou documentos consultados. "
            "O RAG ainda não está implementado nesta versão; "
            "retorne fontes vazias e usou_rag como false. "
            "Se não souber uma informação, deixe isso claro."
        ),
    )


def executar_agente(pergunta: str) -> AgentResponse:
    """Executa o agente para uma pergunta e retorna a resposta validada."""
    result = get_agent().invoke(
        {"messages": [{"role": "user", "content": pergunta}]},
        config={"configurable": {"thread_id": str(uuid4())}},
    )
    structured_response = result.get("structured_response")
    if structured_response is None:
        raise RuntimeError("O agente não retornou uma resposta estruturada.")
    if isinstance(structured_response, AgentResponse):
        return structured_response
    return AgentResponse.model_validate(structured_response)


def main() -> None:
    """Smoke test para executar o agente pelo comando `uv run nexus-ai`."""
    pergunta = "Quem é o professor Gustavo Guanabara?"
    resposta = executar_agente(pergunta)
    print(resposta.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()