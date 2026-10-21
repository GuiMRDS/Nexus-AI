
from langchain.agents import create_agent
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import GROQ_API_KEY, GROQ_LLAMA

# Disponibiliza a chave para a integração com Groq.
# A integração LangChain normalmente também lê GROQ_API_KEY
# diretamente das variáveis de ambiente.

checkpointer = InMemorySaver()

agent = create_agent(
    model=GROQ_LLAMA,
    tools=[],
    checkpointer=checkpointer,
)

config = {
    "configurable": {
        "thread_id": str(uuid7())
    }
}

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "O que é o Nexus_IA?"
            }
        ]
    },
    config=config,
)

print("Resposta 1:", result["messages"][-1].content)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Quais são suas funcionalidades?"
            }
        ]
    },
    config=config,
)

print("Resposta 2:", result["messages"][-1].content)
