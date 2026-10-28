import os
from datetime import date, datetime

from maintenance.avaliacao import (
    Caso,
    avaliar,
    candidato_aprovado,
    carregar_casos,
    usando_modelo,
)
from maintenance.curadoria import relatorio_curadoria
from nexus_ai.schemas import AgentResponse, Fonte, Turno

INVENTARIO = """﻿document_id,document_name,category,source_path,format,version,last_reviewed,curation_status,owner_role,ingestion_method,notes
DOC-001,Base,Produto,documentos/base.md,Markdown,1.0,01/10/2026,Aprovado para demonstração,Responsável de Produto,manual,
DOC-002,FAQ,Suporte,documentos/faq.md,Markdown,1.0,01/01/2026,Aprovado,Responsável de Suporte,manual,
DOC-003,Política,Legal,documentos/politica.md,Markdown,1.0,01/10/2026,Rascunho demonstrativo,Responsável Jurídico,manual,
DOC-004,Preços,Comercial,documentos/precos.csv,CSV,1.0,01/10/2026,Aprovado,Responsável Comercial,manual,
"""


def _arquivo(path, conteudo, modificado_em):
    path.write_text(conteudo, encoding="utf-8")
    instante = datetime.combine(modificado_em, datetime.min.time()).timestamp()
    os.utime(path, (instante, instante))


def test_relatorio_de_curadoria(tmp_path):
    (tmp_path / "05_inventario_documental.csv").write_text(INVENTARIO, encoding="utf-8")
    _arquivo(tmp_path / "base.md", "# Base", date(2026, 9, 30))
    _arquivo(tmp_path / "faq.md", "# FAQ", date(2025, 12, 1))
    _arquivo(tmp_path / "politica.md", "# Política", date(2026, 10, 20))
    _arquivo(tmp_path / "novo.md", "# Sem inventário", date(2026, 10, 1))

    relatorio = relatorio_curadoria(tmp_path, prazo_dias=90, hoje=date(2026, 10, 28))

    motivos = {p["documento"]: " | ".join(p["motivos"]) for p in relatorio["pendencias"]}
    assert "DOC-001" not in motivos
    assert "Revisão vencida" in motivos["DOC-002"]
    assert "Rascunho" in motivos["DOC-003"]
    assert "depois da última revisão" in motivos["DOC-003"]
    assert "precos.csv não está em data/documents" in motivos["DOC-004"]
    # O próprio inventário (.csv) também é um arquivo indexável sem registro.
    assert relatorio["arquivos_sem_inventario"] == ["05_inventario_documental.csv", "novo.md"]


def _resposta(texto, encontrou=True):
    return AgentResponse(
        resposta=texto,
        encontrou_resposta=encontrou,
        usou_rag=encontrou,
        fontes=[Fonte(arquivo="faq.md")] if encontrou else [],
    )


def test_avaliacao_mede_cobertura_e_conteudo():
    casos = [
        Caso("Preço do Pro?", True, ["79,90"], []),
        Caso("Membros do Pro?", True, ["20"], []),
        Caso("Férias?", False, [], []),
        Caso("Capital da Austrália?", False, [], []),
    ]
    respostas = {
        "Preço do Pro?": _resposta("Custa R$ 79.90 por mês."),
        "Membros do Pro?": _resposta("Até 10 membros."),
        "Férias?": _resposta("Não encontrei.", encontrou=False),
        "Capital da Austrália?": _resposta("Canberra."),
    }

    relatorio = avaliar(casos, lambda pergunta, _historico: respostas[pergunta])

    resumo = relatorio["resumo"]
    assert resumo["cobertura"] == 0.75
    assert resumo["conteudo"] == 0.5
    assert resumo["falsos_positivos"] == 1
    assert relatorio["casos"][1]["faltando"] == ["20"]


def test_avaliacao_registra_erro_sem_interromper():
    def falha(_pergunta, _historico):
        raise RuntimeError("rate limit")

    relatorio = avaliar([Caso("Oi?", True, ["x"], [])], falha)

    assert relatorio["resumo"]["erros"] == 1
    assert "rate limit" in relatorio["casos"][0]["erro"]


def test_candidato_so_e_aprovado_sem_piorar():
    base = {"cobertura": 0.9, "conteudo": 0.8, "falsos_positivos": 0, "erros": 0}
    assert candidato_aprovado(base, {**base, "conteudo": 0.85}) is True
    assert candidato_aprovado(base, {**base, "cobertura": 0.85}) is False
    assert candidato_aprovado(base, {**base, "falsos_positivos": 1}) is False
    assert candidato_aprovado(base, {**base, "erros": 2}) is False


def test_usando_modelo_restaura_variavel(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "modelo-atual")
    with usando_modelo("modelo-candidato"):
        assert os.environ["GROQ_MODEL"] == "modelo-candidato"
    assert os.environ["GROQ_MODEL"] == "modelo-atual"


def test_conjunto_de_avaliacao_do_projeto_e_valido():
    casos = carregar_casos()
    assert len(casos) >= 10
    assert any(not caso.deve_responder for caso in casos)
    assert any(caso.historico for caso in casos)
    assert all(isinstance(turno, Turno) for caso in casos for turno in caso.historico)
