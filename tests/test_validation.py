from agents.validation import RespostaGerada, filtrar_por_relevancia, validar_resposta
from processing.retrieval import RetrievedPassage


def passage(text, score=1.0):
    return RetrievedPassage(text=text, metadata={}, vector_distance=None, rerank_score=score)


def gerada(resposta, citados, encontrou=True):
    return RespostaGerada(resposta=resposta, encontrou_resposta=encontrou,
                          documentos_citados=citados)


def test_filtra_trechos_abaixo_do_limiar():
    passages = [passage("a", 5.0), passage("b", -4.0), passage("c", -3.5)]

    assert [p.text for p in filtrar_por_relevancia(passages, -3.5)] == ["a", "c"]


def test_resposta_consistente_nao_tem_problemas():
    passages = [passage("Plano Pro: 79.90 por mês, 20 usuários, suporte em 1 dia útil.")]

    assert validar_resposta(gerada("O Pro custa R$ 79,90 e permite 20 usuários.", [1]),
                            passages) == []


def test_numero_ausente_dos_documentos_citados_e_rejeitado():
    passages = [passage("Plano Pro: 79.90 por mês."), passage("Limite de 50 usuários.")]

    problemas = validar_resposta(gerada("O Pro permite 50 usuários.", [1]), passages)

    assert any("50" in problema for problema in problemas)


def test_referencia_a_documento_nao_conta_como_valor():
    passages = [passage("Sem números aqui."), passage("Nem aqui.")]

    assert validar_resposta(gerada("Conforme o [Documento 2], não há custo.", [2]),
                            passages) == []


def test_numero_da_pergunta_e_aceito():
    passages = [passage("O backup é diário.")]

    assert validar_resposta(gerada("Sim, em 2026 o backup é diário.", [1]), passages,
                            pergunta="Em 2026 o backup é diário?") == []


def test_resposta_afirmativa_sem_citacao_e_rejeitada():
    problemas = validar_resposta(gerada("Sim.", []), [passage("x")])

    assert any("não cita nenhum documento" in problema for problema in problemas)


def test_citacao_inexistente_e_rejeitada():
    problemas = validar_resposta(gerada("Sim.", [3]), [passage("x")])

    assert any("inexistentes" in problema for problema in problemas)


def test_resposta_nao_encontrada_dispensa_validacao():
    assert validar_resposta(gerada("Não encontrei.", [], encontrou=False), []) == []
