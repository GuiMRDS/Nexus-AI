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
