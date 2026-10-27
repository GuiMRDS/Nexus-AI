from processing.store.reranker import Reranker


class FakeCrossEncoder:
    def predict(self, pairs):
        return [float(len(passage)) for _, passage in pairs]


class FakeNumpyLikeCrossEncoder:
    class _Array(list):
        def tolist(self):
            return list(self)

    def predict(self, pairs):
        return self._Array(float(len(passage)) for _, passage in pairs)


def test_score_orders_by_relevance():
    reranker = Reranker(model=FakeCrossEncoder())

    scores = reranker.score("pergunta", ["ab", "abcdef", "abcd"])

    assert scores == [2.0, 6.0, 4.0]


def test_score_accepts_numpy_like_output():
    reranker = Reranker(model=FakeNumpyLikeCrossEncoder())

    scores = reranker.score("pergunta", ["abc", "a"])

    assert scores == [3.0, 1.0]


def test_score_empty_passages_returns_empty_list():
    reranker = Reranker(model=FakeCrossEncoder())

    assert reranker.score("pergunta", []) == []
