from pathlib import Path

import pytest

from processing.store.sync import sync_directory


class FakeStore:
    def __init__(self, persist_directory):
        self.persist_directory = persist_directory
        self.removidos = []

    def delete_by_source_path(self, source_path):
        self.removidos.append(str(source_path))


class FakeIndexer:
    def __init__(self):
        self.chamadas = []
        self.falhar = set()

    def __call__(self, path, *, vector_store, category, enable_ocr):
        if Path(path).name in self.falhar:
            raise ValueError("arquivo corrompido")
        self.chamadas.append((Path(path).name, category))
        return 3


@pytest.fixture
def ambiente(tmp_path):
    docs = tmp_path / "documents"
    (docs / "suporte").mkdir(parents=True)
    (docs / "suporte" / "faq.md").write_text("# FAQ\nconteúdo", encoding="utf-8")
    (docs / "contatos.md").write_text("# Contatos", encoding="utf-8")
    (docs / "imagem.xyz").write_text("ignorado", encoding="utf-8")
    store = FakeStore(tmp_path / "vector_store")
    indexer = FakeIndexer()

    def sync():
        return sync_directory(docs, vector_store=store, indexer=indexer)

    return docs, store, indexer, sync


def test_primeira_execucao_indexa_tudo_com_categoria(ambiente):
    _docs, _store, indexer, sync = ambiente

    resumo = sync()

    assert sorted(indexer.chamadas) == [("contatos.md", "geral"), ("faq.md", "suporte")]
    assert len(resumo["added"]) == 2
    assert resumo["chunks_indexed"] == 6


def test_arquivo_sem_mudanca_nao_e_reindexado(ambiente):
    _docs, _store, indexer, sync = ambiente
    sync()
    indexer.chamadas.clear()

    resumo = sync()

    assert indexer.chamadas == []
    assert resumo["unchanged"] == 2
    assert resumo["added"] == resumo["updated"] == resumo["removed"] == []


def test_arquivo_alterado_e_reindexado(ambiente):
    docs, _store, indexer, sync = ambiente
    sync()
    indexer.chamadas.clear()
    (docs / "suporte" / "faq.md").write_text("# FAQ\nnova versão", encoding="utf-8")

    resumo = sync()

    assert indexer.chamadas == [("faq.md", "suporte")]
    assert [Path(p).name for p in resumo["updated"]] == ["faq.md"]


def test_arquivo_removido_sai_do_indice(ambiente):
    docs, store, _indexer, sync = ambiente
    sync()
    (docs / "contatos.md").unlink()

    resumo = sync()

    assert [Path(p).name for p in resumo["removed"]] == ["contatos.md"]
    assert [Path(p).name for p in store.removidos] == ["contatos.md"]
    # A remoção não se repete na execução seguinte.
    assert sync()["removed"] == []


def test_falha_de_indexacao_e_tentada_de_novo_na_proxima_execucao(ambiente):
    _docs, _store, indexer, sync = ambiente
    indexer.falhar.add("faq.md")

    resumo = sync()
    assert [Path(e["file"]).name for e in resumo["errors"]] == ["faq.md"]

    indexer.falhar.clear()
    resumo = sync()
    assert [Path(p).name for p in resumo["added"]] == ["faq.md"]


def test_outra_pasta_no_mesmo_manifesto_nao_e_removida(ambiente, tmp_path):
    docs, store, indexer, sync = ambiente
    sync()
    outra = tmp_path / "outra"
    outra.mkdir()
    (outra / "extra.md").write_text("# Extra", encoding="utf-8")

    resumo = sync_directory(outra, vector_store=store, indexer=indexer)

    assert resumo["removed"] == []
    assert store.removidos == []
    assert sync()["unchanged"] == 2
