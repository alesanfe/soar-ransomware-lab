"""Unit tests for ShuffleExecutionIndex (OpenSearch read adapter)."""

from __future__ import annotations

from soar_lab.infrastructure.integrations.shuffle.execution_index import (
    EXECUTION_INDEX,
    ShuffleExecutionIndex,
)


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeHTTP:
    def __init__(self, response=None):
        self.response = response or _Resp(200, {"hits": {"hits": []}})
        self.posts = []

    def post(self, url, **kw):
        self.posts.append((url, kw.get("json")))
        return self.response


def _idx(http):
    return ShuffleExecutionIndex("http://os:9200/", http=http)


class TestGetExecution:
    def test_found_returns_source(self):
        doc = {"execution_id": "e1", "status": "FINISHED"}
        http = FakeHTTP(_Resp(200, {"hits": {"hits": [{"_source": doc}]}}))
        assert _idx(http).get_execution("e1") == doc
        should = http.posts[0][1]["query"]["bool"]["should"]
        assert {"terms": {"execution_id": ["e1"]}} in should
        assert {"terms": {"execution_id.keyword": ["e1"]}} in should

    def test_not_found_returns_none(self):
        assert _idx(FakeHTTP()).get_execution("nope") is None

    def test_http_error_returns_none(self):
        assert _idx(FakeHTTP(_Resp(500))).get_execution("e1") is None

    def test_transport_error_returns_none(self):
        class Boom(FakeHTTP):
            def post(self, url, **kw):
                raise ConnectionError("down")

        assert _idx(Boom()).get_execution("e1") is None

    def test_wildcard_index_used(self):
        http = FakeHTTP()
        _idx(http).get_execution("e1")
        assert EXECUTION_INDEX in http.posts[0][0]


class TestRecentExecutions:
    def test_returns_sources_sorted_desc(self):
        docs = [{"execution_id": "a"}, {"execution_id": "b"}]
        http = FakeHTTP(_Resp(200, {"hits": {"hits": [{"_source": d} for d in docs]}}))
        out = _idx(http).recent_executions(20)
        assert [d["execution_id"] for d in out] == ["a", "b"]
        assert http.posts[0][1]["sort"] == [{"started_at": {"order": "desc"}}]

    def test_limit_clamped(self):
        http = FakeHTTP()
        _idx(http).recent_executions(5000)
        assert http.posts[0][1]["size"] == 100
        _idx(http).recent_executions(0)
        assert http.posts[1][1]["size"] == 1
