"""Unit tests for ``StaleExecutionGC`` (RES-01 surgical GC)."""

from __future__ import annotations

from soar_lab.infrastructure.monitoring.stale_execution_gc import (
    EXECUTION_INDEX,
    StaleExecutionGC,
)


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeHTTP:
    """requests-compatible stub recording calls and serving canned replies."""

    def __init__(self, post_responses=None, delete_codes=None):
        self.post_responses = list(post_responses or [])
        self.delete_codes = list(delete_codes or [])
        self.posts = []
        self.deletes = []

    def post(self, url, **kw):
        self.posts.append((url, kw.get("json")))
        return self.post_responses.pop(0) if self.post_responses else _Resp(200, {})

    def delete(self, url, **kw):
        self.deletes.append(url)
        code = self.delete_codes.pop(0) if self.delete_codes else 200
        return _Resp(code)


def _gc(http, stale_minutes=30):
    return StaleExecutionGC(
        os_url="http://os:9200",
        backend_url="http://shuffle:5001",
        api_key="k",
        stale_minutes=stale_minutes,
        http=http,
    )


class _BadJsonResp:
    """HTTP 200 whose body is not JSON (proxy splash, truncated reply)."""

    status_code = 200

    def json(self):
        raise ValueError("Expecting value: line 1 column 1")


class TestMalformedResponses:
    """GC contract: ``collect_once`` must never raise — a malformed 200
    body is a transport-level anomaly, same class as a 5xx, not a reason
    to kill the periodic task. ``find_stale`` currently calls
    ``r.json()`` outside the try, so a non-JSON body propagates
    ``ValueError``/``JSONDecodeError`` out of a method documented as
    never-raising."""

    def test_find_stale_bad_json_returns_empty(self):
        gc = _gc(FakeHTTP(post_responses=[_BadJsonResp()]))
        assert gc.find_stale() == []

    def test_collect_once_bad_json_does_not_raise(self):
        gc = _gc(FakeHTTP(post_responses=[_BadJsonResp()]))
        out = gc.collect_once()
        assert out == {"stale": 0, "marked_aborted": 0, "api_aborted": 0, "api_failed": 0}


class TestFindStale:
    def test_returns_exec_ids_and_doc_ids(self):
        http = FakeHTTP(
            post_responses=[
                _Resp(
                    200,
                    {
                        "hits": {
                            "hits": [
                                {
                                    "_id": "doc1",
                                    "_source": {"execution_id": "e1", "started_at": 100},
                                },
                                {"_id": "doc2", "_source": {"execution_id": "e2"}},
                            ]
                        }
                    },
                )
            ]
        )
        stale = _gc(http).find_stale(now=10_000)
        assert [s["execution_id"] for s in stale] == ["e1", "e2"]
        assert [s["doc_id"] for s in stale] == ["doc1", "doc2"]

    def test_query_filters_executing_and_cutoff(self):
        http = FakeHTTP(post_responses=[_Resp(200, {"hits": {"hits": []}})])
        _gc(http, stale_minutes=30).find_stale(now=10_000)
        body = http.posts[0][1]
        must = body["query"]["bool"]["must"]
        assert {"term": {"status": "EXECUTING"}} in must
        cutoff = must[1]["range"]["started_at"]["lt"]
        assert cutoff == 10_000 - 30 * 60

    def test_missing_index_returns_empty(self):
        http = FakeHTTP(post_responses=[_Resp(404)])
        assert _gc(http).find_stale() == []

    def test_http_error_returns_empty(self):
        http = FakeHTTP(post_responses=[_Resp(500)])
        assert _gc(http).find_stale() == []

    def test_transport_error_returns_empty(self):
        class Boom(FakeHTTP):
            def post(self, url, **kw):
                raise ConnectionError("os down")

        assert _gc(Boom()).find_stale() == []


class TestMarkAborted:
    def test_marks_docs_and_returns_count(self):
        http = FakeHTTP(post_responses=[_Resp(200, {"updated": 3})])
        gc = _gc(http)
        assert gc.mark_aborted(["a", "b", "c"]) == 3
        body = http.posts[0][1]
        assert f"/{EXECUTION_INDEX}/_update_by_query" in http.posts[0][0]
        assert body["query"]["ids"]["values"] == ["a", "b", "c"]
        assert body["script"]["params"]["status"] == "ABORTED"

    def test_empty_list_short_circuits(self):
        http = FakeHTTP()
        assert _gc(http).mark_aborted([]) == 0
        assert http.posts == []


class TestCollectOnce:
    def test_full_pass_aborts_and_marks(self):
        http = FakeHTTP(
            post_responses=[
                _Resp(
                    200,
                    {
                        "hits": {
                            "hits": [
                                {
                                    "_id": "doc1",
                                    "_source": {"execution_id": "e1"},
                                }
                            ]
                        }
                    },
                ),
                _Resp(200, {"updated": 1}),
            ],
            delete_codes=[200],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out == {"stale": 1, "marked_aborted": 1, "api_aborted": 1, "api_failed": 0}
        assert any("/api/v1/executions/e1" in u for u in http.deletes)

    def test_no_stale_is_noop(self):
        http = FakeHTTP(post_responses=[_Resp(200, {"hits": {"hits": []}})])
        out = _gc(http).collect_once()
        assert out["stale"] == 0 and out["marked_aborted"] == 0
        assert http.deletes == []
        assert len(http.posts) == 1  # search only, no update_by_query

    def test_api_abort_failure_still_marks_doc(self):
        """A failed API abort must not prevent freeing the Orborus slot."""
        http = FakeHTTP(
            post_responses=[
                _Resp(
                    200,
                    {
                        "hits": {
                            "hits": [
                                {
                                    "_id": "doc1",
                                    "_source": {"execution_id": "e1"},
                                }
                            ]
                        }
                    },
                ),
                _Resp(200, {"updated": 1}),
            ],
            delete_codes=[500],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["api_failed"] == 1
        assert out["marked_aborted"] == 1

    def test_abort_404_counts_as_success(self):
        """404 means the execution is already gone — slot is free."""
        http = FakeHTTP(
            post_responses=[
                _Resp(
                    200,
                    {
                        "hits": {
                            "hits": [
                                {
                                    "_id": "d",
                                    "_source": {"execution_id": "e1"},
                                }
                            ]
                        }
                    },
                ),
                _Resp(200, {"updated": 1}),
            ],
            delete_codes=[404],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["api_aborted"] == 1

    def test_fresh_executing_not_collected(self):
        """EXECUTING docs inside the threshold must be left alone — the
        _search query carries the range filter; an empty hit page proves
        no doc was touched."""
        http = FakeHTTP(post_responses=[_Resp(200, {"hits": {"hits": []}})])
        out = _gc(http, stale_minutes=30).collect_once(now=3600)
        must = http.posts[0][1]["query"]["bool"]["must"]
        assert must[1]["range"]["started_at"]["lt"] == 3600 - 1800
        assert out["stale"] == 0
