from processing.store.embeddings import EmbeddingService


class FakeModel:
    """Modelo falso para testes, sem download de pesos."""

    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        return [
            [float(len(text)), 1.0]
            for text in texts
        ]


def test_encode_documents():
    service = EmbeddingService(model=FakeModel())

    result = service.encode_documents([
        "abc",
        "abcd",
    ])

    assert result == [
        [3.0, 1.0],
        [4.0, 1.0],
    ]


def test_encode_query():
    service = EmbeddingService(model=FakeModel())

    result = service.encode_query("teste")

    assert result == [5.0, 1.0]


def test_encode_query_rejects_empty_text():
    service = EmbeddingService(model=FakeModel())

    try:
        service.encode_query("   ")
    except ValueError as exc:
        assert "vazia" in str(exc)
    else:
        raise AssertionError(
            "Era esperado ValueError para uma consulta vazia."
        )
