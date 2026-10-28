import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents.formatting import formatar_resposta
from nexus_ai.config import get_groq_model, get_sync_interval_minutes
from nexus_ai.monitoring import MonitoringStore
from nexus_ai.schemas import AgentResponse, AskRequest, FeedbackRequest, Turno

logger = logging.getLogger("nexus_ai")

WEB_DIR = Path(__file__).resolve().parent / "web"
DOCUMENTS_DIR = Path(os.getenv("NEXUS_DOCUMENTS_DIR", "data/documents"))


def _sincronizar_periodicamente(intervalo_min: float, parar: threading.Event) -> None:
    """Mantém o índice em dia usando o mesmo VectorStore que atende as perguntas."""
    from agents.agent import get_retriever
    from processing.store.sync import sync_directory

    while not parar.is_set():
        try:
            resumo = sync_directory(DOCUMENTS_DIR, vector_store=get_retriever().vector_store)
            mudancas = len(resumo["added"]) + len(resumo["updated"]) + len(resumo["removed"])
            if mudancas or resumo["errors"]:
                logger.info("Sincronização de documentos: %s", resumo)
        except Exception:
            logger.exception("Falha na sincronização periódica de documentos.")
        parar.wait(intervalo_min * 60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    intervalo = get_sync_interval_minutes()
    parar = threading.Event()
    if intervalo > 0:
        threading.Thread(
            target=_sincronizar_periodicamente,
            args=(intervalo, parar),
            name="nexus-sync",
            daemon=True,
        ).start()
    yield
    parar.set()


app = FastAPI(
    title="Nexus_IA API",
    description=(
        "API do assistente Nexus_IA. Consulta a documentação local do produto "
        "para responder perguntas sobre planos, funcionalidades, suporte e políticas."
    ),
    version="0.2.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@lru_cache(maxsize=1)
def get_monitoring() -> MonitoringStore:
    return MonitoringStore()


def executar_agente(pergunta: str, historico: list[Turno] | None = None) -> AgentResponse:
    """Carrega o agente sob demanda para permitir testar a API sem inicializá-lo."""
    from agents.agent import executar_agente as executar

    return executar(pergunta, historico)


def _registrar(pergunta: str, response: AgentResponse | None, inicio: float, **extra) -> str | None:
    """Registra a interação sem nunca derrubar a resposta ao usuário."""
    try:
        return get_monitoring().registrar_interacao(
            pergunta,
            response,
            round((time.perf_counter() - inicio) * 1000),
            modelo=get_groq_model(),
            **extra,
        )
    except Exception:
        logger.exception("Não foi possível registrar a interação.")
        return None


@app.get("/", include_in_schema=False)
def interface() -> FileResponse:
    """Chat web do assistente."""
    return FileResponse(WEB_DIR / "index.html")


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
    """Executa o agente e devolve uma resposta JSON validada, formatada para o canal."""
    inicio = time.perf_counter()
    try:
        response = executar_agente(payload.pergunta, payload.historico)
    except ValueError as exc:
        _registrar(payload.pergunta, None, inicio, canal=payload.canal, erro="configuracao")
        # Erros de configuração, como ausência de chave, são reportados sem
        # devolver detalhes internos da aplicação ao consumidor da API.
        raise HTTPException(
            status_code=503,
            detail="O serviço de IA não está configurado corretamente.",
        ) from exc
    except Exception as exc:
        _registrar(payload.pergunta, None, inicio, canal=payload.canal, erro=type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter uma resposta do serviço de IA.",
        ) from exc

    interacao_id = _registrar(payload.pergunta, response, inicio, canal=payload.canal)
    return response.model_copy(
        update={
            "resposta_formatada": formatar_resposta(response, payload.canal),
            "interacao_id": interacao_id,
        }
    )


@app.post(
    "/api/v1/feedback",
    status_code=204,
    tags=["Assistente"],
    summary="Avaliar uma resposta (positivo/negativo)",
)
def feedback(payload: FeedbackRequest) -> Response:
    """Grava a avaliação do colaborador. Enviar de novo substitui a anterior."""
    if not get_monitoring().registrar_feedback(
        payload.interacao_id, payload.avaliacao, payload.motivo
    ):
        raise HTTPException(status_code=404, detail="Interação não encontrada.")
    return Response(status_code=204)


@app.get("/api/v1/metricas", tags=["Manutenção"], summary="Indicadores de qualidade")
def metricas(dias: int = Query(default=30, ge=1, le=365)) -> dict:
    """Perguntas sem resposta, feedback negativo e tempo de resposta do período."""
    return get_monitoring().metricas(dias=dias)


@app.get("/api/v1/curadoria", tags=["Manutenção"], summary="Pendências de curadoria")
def curadoria() -> dict:
    """Documentos com revisão vencida, em rascunho ou alterados depois da revisão."""
    from maintenance.curadoria import relatorio_curadoria

    return relatorio_curadoria(DOCUMENTS_DIR)
