import pytest

from nexus_ai.config import DEFAULT_GROQ_MODEL, get_groq_api_key, get_groq_model


def test_groq_api_key_carregada(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_chave_de_teste")
    assert get_groq_api_key() == "gsk_chave_de_teste"


def test_groq_api_key_ausente(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY não encontrada"):
        get_groq_api_key()


def test_groq_api_key_vazia(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    with pytest.raises(ValueError, match="GROQ_API_KEY não encontrada"):
        get_groq_api_key()

def test_groq_model_configurado(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "  llama-3.3-70b-versatile  ")
    assert get_groq_model() == "llama-3.3-70b-versatile"


def test_groq_model_padrao(monkeypatch):
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    assert get_groq_model() == DEFAULT_GROQ_MODEL


def test_groq_model_vazio_usa_padrao(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "   ")
    assert get_groq_model() == DEFAULT_GROQ_MODEL
