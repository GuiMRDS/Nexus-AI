from pathlib import Path

from agents.document_search import buscar_documentacao, montar_contexto_documental


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = PROJECT_ROOT / "data" / "documents"


def test_busca_limites_plano_gratuito():
    results = buscar_documentacao("Quais são os limites do plano Gratuito?", documents_dir=DOCUMENTS)
    assert results
    combined = "\n".join(result.text for result in results).lower()
    assert "gratuito" in combined
    assert "membros" in combined or "projetos" in combined
    assert any("planos_precos.csv" in result.source or "faq_suporte" in result.source for result in results)


def test_busca_privacidade_e_exclusao():
    results = buscar_documentacao("Como solicito a exclusão da minha conta e dos meus dados?", documents_dir=DOCUMENTS)
    assert results
    assert any("privacidade" in result.source or "faq_suporte" in result.source for result in results)


def test_contexto_vazio_nao_inventa_documentos():
    assert "Nenhum trecho relevante" in montar_contexto_documental([])
