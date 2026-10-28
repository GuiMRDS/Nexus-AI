from agents.contacts import carregar_contatos
from agents.formatting import formatar_resposta
from nexus_ai.schemas import AgentResponse, Fonte
from processing.store.indexing import category_from_path


def test_documento_de_contatos_cobre_todas_as_areas():
    contatos = {contato.categoria: contato.contato for contato in carregar_contatos()}

    assert contatos == {
        "suporte": "suporte@nexus-ia.example",
        "comercial": "comercial@nexus-ia.example",
        "produto": "produto@nexus-ia.example",
        "privacidade-legal": "privacidade@nexus-ia.example",
    }


def test_contatos_ausentes_devolvem_lista_vazia(tmp_path):
    assert carregar_contatos(tmp_path / "nao_existe.md") == []


def test_categoria_vem_da_subpasta(tmp_path):
    assert category_from_path(tmp_path / "suporte" / "faq.md", tmp_path) == "suporte"
    assert category_from_path(tmp_path / "contatos.md", tmp_path) == "geral"


RESPOSTA = AgentResponse(
    resposta="O plano Pro custa R$ 79,90 por mês.",
    fontes=[
        Fonte(arquivo="04_planos_precos.csv", localizacao="linhas 2-4",
              atualizado_em="2026-10-21"),
        Fonte(arquivo="02_faq_suporte.md", secao="Planos"),
    ],
    usou_rag=True,
    encontrou_resposta=True,
)


def test_formato_chat_tem_resumo_seguido_das_fontes():
    texto = formatar_resposta(RESPOSTA, "chat")

    assert texto.startswith("O plano Pro custa R$ 79,90 por mês.")
    assert "**Fontes**" in texto
    assert "1. 04_planos_precos.csv — linhas 2-4 · atualizado em 2026-10-21" in texto
    assert "2. 02_faq_suporte.md — Planos" in texto


def test_formato_email_tem_saudacao_e_referencias():
    texto = formatar_resposta(RESPOSTA, "email")

    assert texto.startswith("Olá,")
    assert "Referências consultadas:" in texto
    assert texto.endswith("Assistente Nexus_IA")


def test_formato_texto_nao_usa_markdown():
    texto = formatar_resposta(RESPOSTA, "texto")

    assert "**" not in texto
    assert "- 02_faq_suporte.md — Planos" in texto


def test_resposta_sem_fontes_nao_mostra_secao_de_fontes():
    texto = formatar_resposta(AgentResponse(resposta="Não encontrei."), "chat")

    assert texto == "Não encontrei."
