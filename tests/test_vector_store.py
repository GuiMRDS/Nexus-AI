from dataclasses import dataclass, field

from processing.store.vector_store import VectorStore


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


class FakeEmbeddingService:
    def encode_documents(self, texts):
        return [
            [float(len(text)), 1.0]
            for text in texts
        ]

    def encode_query(self, query):
        return [float(len(query)), 1.0]


class FakeCollection:
    """Coleção em memória para testes sem ChromaDB."""

    def __init__(self):
        self.items = {}

    def upsert(
        self,
        ids,
        documents,
        metadatas,
        embeddings,
    ):
        for item_id, document, metadata, embedding in zip(
            ids,
            documents,
            metadatas,
            embeddings,
        ):
            self.items[item_id] = {
                "document": document,
                "metadata": metadata,
                "embedding": embedding,
            }

    def query(
        self,
        query_embeddings,
        n_results,
        where=None,
        include=None,
    ):
        items = list(self.items.items())

        if where:
            key, value = next(iter(where.items()))
            items = [
                (item_id, item)
                for item_id, item in items
                if item["metadata"].get(key) == value
            ]

        items = items[:n_results]

        return {
            "ids": [[item_id for item_id, _ in items]],
            "documents": [
                [item["document"] for _, item in items]
            ],
            "metadatas": [
                [item["metadata"] for _, item in items]
            ],
            "distances": [
                [0.1 for _ in items]
            ],
        }

    def get(self, where=None, include=None):
        items = list(self.items.items())

        if where:
            key, value = next(iter(where.items()))
            items = [
                (item_id, item)
                for item_id, item in items
                if item["metadata"].get(key) == value
            ]

        return {
            "ids": [item_id for item_id, _ in items],
            "metadatas": [
                item["metadata"] for _, item in items
            ],
        }

    def delete(self, ids=None, where=None):
        if ids is not None:
            for item_id in ids:
                self.items.pop(item_id, None)

        elif where:
            key, value = next(iter(where.items()))

            for item_id in list(self.items):
                if self.items[item_id]["metadata"].get(key) == value:
                    del self.items[item_id]


def make_store():
    return VectorStore(
        embedding_service=FakeEmbeddingService(),
        collection=FakeCollection(),
    )


def test_upsert_chunks_and_search():
    store = make_store()

    count = store.upsert_chunks([
        Chunk(
            "Conteúdo de teste",
            {
                "source_path": "doc.pdf",
                "category": "geral",
            },
        )
    ])

    assert count == 1

    results = store.search(
        "conteúdo",
        limit=3,
    )

    assert len(results) == 1
    assert results[0].text == "Conteúdo de teste"


def test_search_supports_metadata_filter():
    store = make_store()

    store.upsert_chunks([
        Chunk(
            "Documento A",
            {
                "source_path": "a.pdf",
                "category": "financeiro",
            },
        ),
        Chunk(
            "Documento B",
            {
                "source_path": "b.pdf",
                "category": "juridico",
            },
        ),
    ])

    results = store.search(
        "documento",
        where={"category": "financeiro"},
    )

    assert len(results) == 1
    assert results[0].metadata["category"] == "financeiro"
