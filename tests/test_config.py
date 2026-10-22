import pytest

from nexus_ai.config import get_groq_api_key


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