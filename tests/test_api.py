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
    def fake_executar_agente(pergunta: str, historico=None) -> AgentResponse:
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
    def fake_executar_agente(_pergunta: str, _historico=None):
        raise ValueError("chave ausente")

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    response = client.post("/api/v1/perguntar", json={"pergunta": "Olá"})
    assert response.status_code == 503


def test_perguntar_trata_erro_do_provedor(monkeypatch):
    def fake_executar_agente(_pergunta: str, _historico=None):
        raise RuntimeError("erro interno de teste")

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    response = client.post("/api/v1/perguntar", json={"pergunta": "Olá"})
    assert response.status_code == 502

def test_perguntar_formata_resposta_para_o_canal(monkeypatch):
    def fake_executar_agente(_pergunta: str, _historico=None) -> AgentResponse:
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


def test_interface_web_e_servida_na_raiz():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Agente de IA" in response.text
    assert client.get("/static/app.js").status_code == 200


def test_perguntar_repassa_historico_da_sessao(monkeypatch):
    recebido = {}

    def fake_executar_agente(pergunta, historico=None):
        recebido["historico"] = historico
        return AgentResponse(resposta="Até 20 membros.", usou_rag=True, encontrou_resposta=True)

    monkeypatch.setattr(api_module, "executar_agente", fake_executar_agente)
    historico = [{"pergunta": f"P{i}", "resposta": f"R{i}"} for i in range(5)]
    response = client.post(
        "/api/v1/perguntar",
        json={"pergunta": "E quantos membros?", "historico": historico},
    )
    assert response.status_code == 200
    # Só os últimos turnos chegam ao agente.
    assert [turno.pergunta for turno in recebido["historico"]] == ["P2", "P3", "P4"]


def test_interacao_registrada_recebe_feedback_e_entra_nas_metricas(monkeypatch):
    respostas = iter([
        AgentResponse(resposta="R$ 79,90.", usou_rag=True, encontrou_resposta=True,
                      fontes=[Fonte(arquivo="04_planos_precos.csv")]),
        AgentResponse(resposta="Não encontrei essa informação.", encontrou_resposta=False),
    ])
    monkeypatch.setattr(api_module, "executar_agente", lambda *_args: next(respostas))

    primeira = client.post("/api/v1/perguntar", json={"pergunta": "Quanto custa o Pro?"}).json()
    client.post("/api/v1/perguntar", json={"pergunta": "Quantos dias de férias?"})
    assert primeira["interacao_id"]

    feedback = client.post(
        "/api/v1/feedback",
        json={"interacao_id": primeira["interacao_id"], "avaliacao": "negativo", "motivo": "Incompleta"},
    )
    assert feedback.status_code == 204

    metricas = client.get("/api/v1/metricas?dias=7").json()
    assert metricas["total_perguntas"] == 2
    assert metricas["sem_resposta"] == 1
    assert metricas["taxa_sem_resposta"] == 0.5
    assert metricas["feedback"] == {"positivo": 0, "negativo": 1, "taxa_negativa": 1.0}
    assert metricas["perguntas_sem_resposta"][0]["pergunta"] == "Quantos dias de férias?"
    assert metricas["respostas_mal_avaliadas"][0]["motivo"] == "Incompleta"


def test_erro_do_agente_e_registrado_sem_contar_como_sem_resposta(monkeypatch):
    def falha(*_args):
        raise RuntimeError("timeout")

    monkeypatch.setattr(api_module, "executar_agente", falha)
    client.post("/api/v1/perguntar", json={"pergunta": "Olá"})

    metricas = client.get("/api/v1/metricas").json()
    assert metricas["total_perguntas"] == 1
    assert metricas["erros"] == 1
    assert metricas["sem_resposta"] == 0


def test_feedback_para_interacao_inexistente_retorna_404():
    response = client.post(
        "/api/v1/feedback", json={"interacao_id": "nao-existe", "avaliacao": "positivo"}
    )
    assert response.status_code == 404


def test_feedback_rejeita_avaliacao_desconhecida():
    response = client.post("/api/v1/feedback", json={"interacao_id": "x", "avaliacao": "talvez"})
    assert response.status_code == 422


def test_curadoria_endpoint_lista_pendencias():
    body = client.get("/api/v1/curadoria").json()
    assert {"pendencias", "arquivos_sem_inventario", "prazo_dias"} <= body.keys()
