from fastapi import FastAPI, HTTPException

from nexus_ai.schemas import AgentResponse, AskRequest

app = FastAPI(
    title="Nexus_IA API",
    description=(
        "API do assistente Nexus_IA. As respostas são estruturadas em JSON. "
        "A recuperação de documentos (RAG) ainda não está habilitada."
    ),
    version="0.1.0",
)


def executar_agente(pergunta: str) -> AgentResponse:
    """Carrega o agente sob demanda para permitir testar a API sem inicializá-lo."""
    from agents.agent import executar_agente as executar

    return executar(pergunta)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    """Verifica se a API está no ar sem chamar o provedor de IA."""
    return {"status": "ok", "service": "nexus-ai"}


@app.post(
    "/api/v1/perguntar",
    response_model=AgentResponse,
    tags=["Assistente"],
    summary="Enviar uma pergunta ao Nexus_IA",
)
def perguntar(payload: AskRequest) -> AgentResponse:
    """Executa o agente e devolve uma resposta JSON validada."""
    try:
        return executar_agente(payload.pergunta)
    except ValueError as exc:
        # Erros de configuração, como ausência de chave, são reportados sem
        # devolver detalhes internos da aplicação ao consumidor da API.
        raise HTTPException(
            status_code=503,
            detail="O serviço de IA não está configurado corretamente.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter uma resposta do serviço de IA.",
        ) from exc