from processing.store.indexing import index_document
from processing.store.vector_store import VectorStore


class FakeEmbeddingService:
    def encode_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeCollection:
    def __init__(self):
        self.items = {}

    def upsert(self, ids, documents, metadatas, embeddings):
        for item_id, document, metadata in zip(ids, documents, metadatas):
            self.items[item_id] = {"document": document, "metadata": metadata}

    def delete(self, where):
        key, value = next(iter(where.items()))
        for item_id in list(self.items):
            if self.items[item_id]["metadata"].get(key) == value:
                del self.items[item_id]


def test_reindexar_arquivo_alterado_remove_trechos_antigos(tmp_path):
    document = tmp_path / "faq.md"
    collection = FakeCollection()
    store = VectorStore(embedding_service=FakeEmbeddingService(), collection=collection)

    document.write_text("# FAQ\n\nO prazo de resposta é de 3 dias úteis.", encoding="utf-8")
    index_document(document, vector_store=store, category="suporte", enable_ocr=False)
    document.write_text("# FAQ\n\nO prazo de resposta é de 1 dia útil.", encoding="utf-8")
    index_document(document, vector_store=store, category="suporte", enable_ocr=False)

    textos = [item["document"] for item in collection.items.values()]
    assert any("1 dia útil" in texto for texto in textos)
    assert not any("3 dias úteis" in texto for texto in textos)
    assert all(item["metadata"]["category"] == "suporte" for item in collection.items.values())
