import os
from functools import lru_cache

from dotenv import load_dotenv

# Carrega as variáveis do .env na inicialização do pacote de configuração.
load_dotenv()


@lru_cache(maxsize=4)
def _segredo_do_vault(secret_ocid: str) -> str:
    from nexus_ai.oci_cloud import ler_segredo

    return ler_segredo(secret_ocid)


def get_groq_api_key() -> str:
    """Retorna a chave da Groq ou lança erro se ela não estiver configurada.

    Localmente, vem de GROQ_API_KEY (.env). Na OCI, NEXUS_GROQ_SECRET_OCID aponta
    para o segredo no OCI Vault, e a chave nunca fica em variável de ambiente.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()

    secret_ocid = os.getenv("NEXUS_GROQ_SECRET_OCID", "").strip()
    if secret_ocid:
        api_key = _segredo_do_vault(secret_ocid)
        if api_key:
            return api_key
        raise ValueError("O segredo da Groq no OCI Vault está vazio.")

    raise ValueError(
        "GROQ_API_KEY não encontrada. Configure essa variável no arquivo .env."
    )

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


def get_sync_interval_minutes() -> float:
    """Intervalo da sincronização automática de documentos dentro da API.

    Configurável por NEXUS_SYNC_INTERVALO_MIN. Zero ou ausente desativa; nesse
    caso a sincronização fica a cargo de scripts/sync_documents.py.
    """
    value = os.getenv("NEXUS_SYNC_INTERVALO_MIN", "").strip()
    if not value:
        return 0.0
    try:
        return max(float(value), 0.0)
    except ValueError as exc:
        raise ValueError("NEXUS_SYNC_INTERVALO_MIN deve ser um número.") from exc


def get_documents_bucket() -> tuple[str, str] | None:
    """Bucket do OCI Object Storage com os documentos originais e o prefixo.

    Configurável por NEXUS_DOCUMENTS_BUCKET e NEXUS_DOCUMENTS_PREFIX. Ausente,
    a sincronização usa só a pasta local.
    """
    bucket = os.getenv("NEXUS_DOCUMENTS_BUCKET", "").strip()
    if not bucket:
        return None
    return bucket, os.getenv("NEXUS_DOCUMENTS_PREFIX", "").strip()
