from uuid import uuid4

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from my_models import GROQ_MODEL_OPENIA
from my_keys import GROQ_API_KEY


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

    print(f"\nPergunta: {question}")
    print(f"Resposta: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()