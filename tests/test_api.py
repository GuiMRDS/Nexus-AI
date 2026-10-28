from fastapi.testclient import TestClient

from nexus_ai.api import app
from nexus_ai.schemas import AgentResponse, Fonte
import nexus_ai.api as api_module

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nexus-ai"}


def test_perguntar_resposta_valida(monkeypatch):
    def fake_executar_agente(pergunta: str) -> AgentResponse:
        assert pergunta == "Quais são os limites do plano Gratuito?"
        return AgentResponse(
            resposta="Resposta de teste.",
            fontes=[],
            usou_rag=False,
        )

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    response = client.post(
        "/api/v1/perguntar",
        json={"pergunta": "Quais são os limites do plano Gratuito?"},
    )
    assert response.status_code == 200
    assert response.json()["resposta"] == "Resposta de teste."
    assert response.json()["fontes"] == []
    assert response.json()["usou_rag"] is False


def test_perguntar_rejeita_pergunta_vazia():
    response = client.post("/api/v1/perguntar", json={"pergunta": "   "})
    assert response.status_code == 422


def test_perguntar_trata_erro_de_configuracao(monkeypatch):
    def fake_executar_agente(_pergunta: str):
        raise ValueError("chave ausente")

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    response = client.post("/api/v1/perguntar", json={"pergunta": "Olá"})
    assert response.status_code == 503


def test_perguntar_trata_erro_do_provedor(monkeypatch):
    def fake_executar_agente(_pergunta: str):
        raise RuntimeError("erro interno de teste")

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    response = client.post("/api/v1/perguntar", json={"pergunta": "Olá"})
    assert response.status_code == 502

def test_perguntar_formata_resposta_para_o_canal(monkeypatch):
    def fake_executar_agente(_pergunta: str) -> AgentResponse:
        return AgentResponse(
            resposta="O plano Pro custa R$ 79,90.",
            fontes=[Fonte(arquivo="04_planos_precos.csv", localizacao="linhas 2-4")],
            usou_rag=True,
            encontrou_resposta=True,
        )

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    response = client.post(
        "/api/v1/perguntar",
        json={"pergunta": "Quanto custa o Pro?", "canal": "email"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fontes"][0]["arquivo"] == "04_planos_precos.csv"
    assert body["resposta_formatada"].startswith("Olá,")
    assert "04_planos_precos.csv — linhas 2-4" in body["resposta_formatada"]


def test_perguntar_rejeita_canal_desconhecido():
    response = client.post("/api/v1/perguntar", json={"pergunta": "Olá", "canal": "fax"})
    assert response.status_code == 422
