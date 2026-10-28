import pytest

import agents.agent as agent_module
from agents.validation import RespostaGerada
from processing.retrieval import RetrievedPassage


def passage(text, score, **metadata):
    return RetrievedPassage(
        text=text,
        metadata={"source_file": "02_faq_suporte.pdf", "category": "suporte", **metadata},
        vector_distance=0.3,
        rerank_score=score,
    )


class FakeRetriever:
    def __init__(self, passages):
        self.passages = passages

    def retrieve(self, query, *, limit=5, candidate_limit=20, where=None):
        return self.passages


class FakeAgent:
    """Devolve as respostas na ordem e guarda as mensagens recebidas."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.mensagens = []

    def invoke(self, payload, config=None):
        self.mensagens.append(payload["messages"][0]["content"])
        return {"structured_response": self.respostas.pop(0)}


@pytest.fixture
def configurar(monkeypatch):
    monkeypatch.setenv("NEXUS_MIN_RELEVANCE", "0")

    def _configurar(passages, *respostas):
        fake_agent = FakeAgent(*respostas)
        monkeypatch.setattr(agent_module, "get_retriever", lambda: FakeRetriever(passages))
        monkeypatch.setattr(agent_module, "get_agent", lambda: fake_agent)
        return fake_agent

    return _configurar


def test_resposta_valida_usa_metadados_reais_como_fonte(configurar):
    fake_agent = configurar(
        [
            passage("O plano Pro custa 79.90 por mês.", 5.0, section_title="Planos",
                    location_type="page", location=2,
                    file_modified_at="2026-10-21T01:06:14+00:00"),
            passage("Outro trecho.", 1.0),
        ],
        RespostaGerada(resposta="O plano Pro custa R$ 79,90 por mês.",
                       encontrou_resposta=True, documentos_citados=[1, 1]),
    )

    response = agent_module.executar_agente("Quanto custa o plano Pro?")

    assert response.encontrou_resposta is True
    assert response.usou_rag is True
    assert len(response.fontes) == 1
    fonte = response.fontes[0]
    assert (fonte.arquivo, fonte.secao, fonte.localizacao, fonte.area, fonte.atualizado_em) == (
        "02_faq_suporte.pdf", "Planos", "página 2", "suporte", "2026-10-21"
    )
    assert "[Documento 1]" in fake_agent.mensagens[0]


def test_sem_trecho_acima_do_limiar_nao_chama_o_llm(configurar, monkeypatch):
    monkeypatch.setenv("NEXUS_MIN_RELEVANCE", "2")
    fake_agent = configurar([passage("Trecho pouco relevante.", 1.5)])

    response = agent_module.executar_agente("Quantos dias de férias eu tenho?")

    assert fake_agent.mensagens == []
    assert response.encontrou_resposta is False
    assert response.fontes == []
    assert agent_module.RESPOSTA_NAO_ENCONTRADA in response.resposta


def test_fallback_sugere_contatos_das_areas(configurar):
    configurar([])

    response = agent_module.executar_agente("Qual o horário do refeitório?")

    assert "suporte@nexus-ia.example" in response.resposta
    assert "comercial@nexus-ia.example" in response.resposta
    assert "privacidade@nexus-ia.example" in response.resposta


def test_modelo_admite_que_nao_sabe_vira_fallback(configurar):
    configurar(
        [passage("Termos de uso.", 3.0)],
        RespostaGerada(resposta="Não sei.", encontrou_resposta=False),
    )

    response = agent_module.executar_agente("Como calculo meu imposto de renda?")

    assert response.encontrou_resposta is False
    assert response.usou_rag is False
    assert agent_module.RESPOSTA_NAO_ENCONTRADA in response.resposta


def test_resposta_sem_respaldo_e_regenerada(configurar):
    fake_agent = configurar(
        [passage("O plano Gratuito permite 3 usuários.", 4.0)],
        RespostaGerada(resposta="O plano Gratuito permite 10 usuários.",
                       encontrou_resposta=True, documentos_citados=[1]),
        RespostaGerada(resposta="O plano Gratuito permite 3 usuários.",
                       encontrou_resposta=True, documentos_citados=[1]),
    )

    response = agent_module.executar_agente("Quantos usuários no plano Gratuito?")

    assert response.resposta == "O plano Gratuito permite 3 usuários."
    assert len(fake_agent.mensagens) == 2
    assert "REJEITADA" in fake_agent.mensagens[1]
    assert "10" in fake_agent.mensagens[1]


def test_resposta_invalida_duas_vezes_vira_fallback(configurar):
    invalida = RespostaGerada(resposta="Custa 999 reais.", encontrou_resposta=True,
                              documentos_citados=[1])
    configurar([passage("O plano Pro custa 79.90.", 4.0)], invalida, invalida)

    response = agent_module.executar_agente("Quanto custa o plano Pro?")

    assert response.encontrou_resposta is False
    assert "999" not in response.resposta


class RetrieverPorConsulta:
    """Só encontra trechos quando a consulta contém o termo esperado."""

    def __init__(self, termo, passages):
        self.termo = termo
        self.passages = passages
        self.consultas = []

    def retrieve(self, query, *, limit=5, candidate_limit=20, where=None):
        self.consultas.append(query)
        return self.passages if self.termo in query else []


def test_pergunta_de_continuacao_usa_a_pergunta_anterior_na_busca(configurar, monkeypatch):
    from nexus_ai.schemas import Turno

    fake_agent = configurar(
        [],
        RespostaGerada(resposta="Até 100 membros.", encontrou_resposta=True, documentos_citados=[1]),
    )
    retriever = RetrieverPorConsulta(
        "Empresarial", [passage("O plano Empresarial permite até 100 membros.", 5.0)]
    )
    monkeypatch.setattr(agent_module, "get_retriever", lambda: retriever)
    historico = [Turno(pergunta="Quanto custa o plano Empresarial?", resposta="R$ 249,90.")]

    response = agent_module.executar_agente("E quantos membros ele permite?", historico)

    assert response.encontrou_resposta is True
    assert retriever.consultas == [
        "E quantos membros ele permite?",
        "Quanto custa o plano Empresarial? E quantos membros ele permite?",
    ]
    assert "CONVERSA ANTERIOR" in fake_agent.mensagens[0]
    assert "Quanto custa o plano Empresarial?" in fake_agent.mensagens[0]


def test_historico_nao_e_usado_na_busca_quando_a_pergunta_basta(configurar, monkeypatch):
    from nexus_ai.schemas import Turno

    configurar(
        [],
        RespostaGerada(resposta="R$ 79,90.", encontrou_resposta=True, documentos_citados=[1]),
    )
    retriever = RetrieverPorConsulta("Pro", [passage("O plano Pro custa 79,90.", 5.0)])
    monkeypatch.setattr(agent_module, "get_retriever", lambda: retriever)

    agent_module.executar_agente(
        "Quanto custa o plano Pro?",
        [Turno(pergunta="Quais perfis existem?", resposta="Administrador e Membro.")],
    )

    assert retriever.consultas == ["Quanto custa o plano Pro?"]
