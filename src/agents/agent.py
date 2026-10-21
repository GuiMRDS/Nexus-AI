
from uuid import uuid4

from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from my_models import GROQ_MODEL_OPENIA
from my_keys import GROQ_API_KEY


class AgentResponse(BaseModel):
    resposta: str = Field(
        description="Resposta em linguagem natural para o usuário."
    )
    fontes: list[str] = Field(
        default_factory=list,
        description="Fontes utilizadas para elaborar a resposta."
    )
    usou_rag: bool = Field(
        default=False,
        description="Indica se a resposta utilizou recuperação de documentos."
    )


def main() -> None:
    model = ChatGroq(
        model=GROQ_MODEL_OPENIA,
        api_key=GROQ_API_KEY,
        temperature=0,
    )

    checkpointer = InMemorySaver()

    agent = create_agent(
        model=model,
        tools=[],
        checkpointer=checkpointer,
        response_format=AgentResponse,
        system_prompt=(
            "Responda em português brasileiro. "
            "Não invente fontes ou documentos consultados. "
            "Como o RAG ainda não está implementado, "
            "retorne fontes vazias e usou_rag como false."
        ),
    )

    config = {
        "configurable": {
            "thread_id": str(uuid4())
        }
    }

    question = "Quem é o professor Gustavo Guanabara?"

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        },
        config=config,
    )

    response: AgentResponse = result["structured_response"]

    print("\nResposta JSON:")
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
