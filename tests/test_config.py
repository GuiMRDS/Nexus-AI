import pytest

from nexus_ai.config import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_MIN_RELEVANCE,
    get_groq_api_key,
    get_groq_model,
    get_min_relevance,
)


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


def test_min_relevance_padrao(monkeypatch):
    monkeypatch.delenv("NEXUS_MIN_RELEVANCE", raising=False)
    assert get_min_relevance() == DEFAULT_MIN_RELEVANCE


def test_min_relevance_configurado(monkeypatch):
    monkeypatch.setenv("NEXUS_MIN_RELEVANCE", "-2.5")
    assert get_min_relevance() == -2.5


def test_min_relevance_invalido(monkeypatch):
    monkeypatch.setenv("NEXUS_MIN_RELEVANCE", "alto")
    with pytest.raises(ValueError, match="NEXUS_MIN_RELEVANCE"):
        get_min_relevance()


def test_sync_interval_desativado_por_padrao(monkeypatch):
    from nexus_ai.config import get_sync_interval_minutes

    monkeypatch.delenv("NEXUS_SYNC_INTERVALO_MIN", raising=False)
    assert get_sync_interval_minutes() == 0.0
    monkeypatch.setenv("NEXUS_SYNC_INTERVALO_MIN", "15")
    assert get_sync_interval_minutes() == 15.0
    monkeypatch.setenv("NEXUS_SYNC_INTERVALO_MIN", "abc")
    with pytest.raises(ValueError):
        get_sync_interval_minutes()
