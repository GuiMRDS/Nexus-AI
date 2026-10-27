import pytest

from processing.retrieval import Retriever, RetrievedPassage, montar_contexto_vetorial
from processing.store.vector_store import VectorStore


class Chunk:
    def __init__(self, text, metadata):
        self.text = text
        self.metadata = metadata


class FakeEmbeddingService:
    def encode_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def encode_query(self, query):
        return [float(len(query)), 1.0]


class FakeCollection:
    """Coleção em memória que preserva a ordem de inserção, sem matemática vetorial real."""

    def __init__(self):
        self.items = {}

    def upsert(self, ids, documents, metadatas, embeddings):
        for item_id, document, metadata, embedding in zip(ids, documents, metadatas, embeddings):
            self.items[item_id] = {
                "document": document,
                "metadata": metadata,
                "embedding": embedding,
            }

    def query(self, query_embeddings, n_results, where=None, include=None):
        items = list(self.items.items())

        if where:
            key, value = next(iter(where.items()))
            items = [(item_id, item) for item_id, item in items if item["metadata"].get(key) == value]

        items = items[:n_results]

        return {
            "ids": [[item_id for item_id, _ in items]],
            "documents": [[item["document"] for _, item in items]],
            "metadatas": [[item["metadata"] for _, item in items]],
            "distances": [[0.1 for _ in items]],
        }


class FakeReranker:
    def __init__(self, scores_by_text):
        self.scores_by_text = scores_by_text

    def score(self, query, passages):
        return [self.scores_by_text[passage] for passage in passages]


def make_store():
    return VectorStore(embedding_service=FakeEmbeddingService(), collection=FakeCollection())


def test_retrieve_reorders_candidates_by_rerank_score():
    store = make_store()
    store.upsert_chunks([
        Chunk("Texto A", {"source_file": "a.pdf"}),
        Chunk("Texto B", {"source_file": "b.pdf"}),
        Chunk("Texto C", {"source_file": "c.pdf"}),
    ])
    reranker = FakeReranker({"Texto A": 1.0, "Texto B": 3.0, "Texto C": 2.0})
    retriever = Retriever(vector_store=store, reranker=reranker)

    passages = retriever.retrieve("pergunta", limit=3, candidate_limit=3)

    assert [passage.text for passage in passages] == ["Texto B", "Texto C", "Texto A"]


def test_retrieve_limit_truncates_after_rerank():
    store = make_store()
    store.upsert_chunks([
        Chunk("Texto A", {"source_file": "a.pdf"}),
        Chunk("Texto B", {"source_file": "b.pdf"}),
        Chunk("Texto C", {"source_file": "c.pdf"}),
    ])
    reranker = FakeReranker({"Texto A": 1.0, "Texto B": 3.0, "Texto C": 2.0})
    retriever = Retriever(vector_store=store, reranker=reranker)

    passages = retriever.retrieve("pergunta", limit=2, candidate_limit=3)

    assert [passage.text for passage in passages] == ["Texto B", "Texto C"]


def test_retrieve_applies_metadata_filter_before_rerank():
    store = make_store()
    store.upsert_chunks([
        Chunk("Documento financeiro", {"source_file": "a.pdf", "category": "financeiro"}),
        Chunk("Documento juridico", {"source_file": "b.pdf", "category": "juridico"}),
    ])
    reranker = FakeReranker({"Documento financeiro": 1.0, "Documento juridico": 1.0})
    retriever = Retriever(vector_store=store, reranker=reranker)

    passages = retriever.retrieve("documento", where={"category": "financeiro"})

    assert len(passages) == 1
    assert passages[0].metadata["category"] == "financeiro"


def test_retrieve_empty_store_returns_empty_list():
    store = make_store()
    retriever = Retriever(vector_store=store, reranker=FakeReranker({}))

    assert retriever.retrieve("qualquer pergunta") == []


def test_retrieve_rejects_candidate_limit_smaller_than_limit():
    store = make_store()
    retriever = Retriever(vector_store=store, reranker=FakeReranker({}))

    with pytest.raises(ValueError):
        retriever.retrieve("pergunta", limit=5, candidate_limit=2)


def test_contexto_vazio_nao_inventa_documentos():
    assert "Nenhum trecho relevante" in montar_contexto_vetorial([])


def test_contexto_inclui_arquivo_secao_e_data():
    passage = RetrievedPassage(
        text="Conteúdo do trecho.",
        metadata={
            "source_file": "politica_ferias.pdf",
            "section_title": "Licença remunerada",
            "file_modified_at": "2026-01-10T00:00:00+00:00",
        },
        vector_distance=0.2,
        rerank_score=4.5,
    )

    contexto = montar_contexto_vetorial([passage])

    assert "politica_ferias.pdf" in contexto
    assert "Licença remunerada" in contexto
    assert "2026-01-10T00:00:00+00:00" in contexto
    assert "Conteúdo do trecho." in contexto
