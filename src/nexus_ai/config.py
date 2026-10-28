import os

from dotenv import load_dotenv

# Carrega as variáveis do .env na inicialização do pacote de configuração.
load_dotenv()


def get_groq_api_key() -> str:
    """Retorna a chave da Groq ou lança erro se ela não estiver configurada."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "GROQ_API_KEY não encontrada. Configure essa variável no arquivo .env."
        )
    return api_key.strip()

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


def get_groq_model() -> str:
    """Retorna o modelo da Groq definido em GROQ_MODEL ou o modelo padrão."""
    model = os.getenv("GROQ_MODEL", "").strip()
    return model or DEFAULT_GROQ_MODEL


# O cross-encoder padrão devolve logits (podem ser negativos). Calibrado com os
# documentos de data/documents: perguntas cobertas ficaram acima de -3,1 e a
# maioria das perguntas fora do escopo abaixo de -3,5.
DEFAULT_MIN_RELEVANCE = -3.5


def get_min_relevance() -> float:
    """Score mínimo do reranker para um trecho ser usado como contexto.

    Configurável por NEXUS_MIN_RELEVANCE. Abaixo dele, o agente não tenta
    gerar resposta e informa que não encontrou a informação.
    """
    value = os.getenv("NEXUS_MIN_RELEVANCE", "").strip()
    if not value:
        return DEFAULT_MIN_RELEVANCE
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError("NEXUS_MIN_RELEVANCE deve ser um número.") from exc
