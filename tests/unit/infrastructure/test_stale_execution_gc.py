"""Unit tests for ``StaleExecutionGC`` (RES-01 / TMO-001 state machine)."""

from __future__ import annotations

from soar_lab.infrastructure.monitoring.stale_execution_gc import (
    EXECUTION_INDEX,
    MAX_CONFIRM_ATTEMPTS,
    StaleExecutionGC,
)


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeHTTP:
    """requests-compatible stub serving canned replies per verb."""

    def __init__(self, post_responses=None, delete_codes=None, get_responses=None):
        self.post_responses = list(post_responses or [])
        self.delete_codes = list(delete_codes or [])
        self.get_responses = list(get_responses or [])
        self.posts = []
        self.deletes = []
        self.gets = []

    def post(self, url, **kw):
        self.posts.append((url, kw.get("json")))
        return self.post_responses.pop(0) if self.post_responses else _Resp(200, {})

    def delete(self, url, **kw):
        self.deletes.append(url)
        code = self.delete_codes.pop(0) if self.delete_codes else 200
        return _Resp(code)

    def get(self, url, **kw):
        self.gets.append(url)
        return self.get_responses.pop(0) if self.get_responses else _Resp(404)


def _gc(http, stale_minutes=30):
    return StaleExecutionGC(
        os_url="http://os:9200",
        backend_url="http://shuffle:5001",
        api_key="k",
        stale_minutes=stale_minutes,
        http=http,
    )


def _hits(*docs):
    return {"hits": {"hits": [{"_id": d[0], "_source": d[1]} for d in docs]}}


def _updated(n=1):
    return _Resp(200, {"result": "updated"})


class _BadJsonResp:
    status_code = 200

    def json(self):
        raise ValueError("Expecting value: line 1 column 1")


class TestMalformedResponses:
    def test_find_stale_bad_json_returns_empty(self):
        gc = _gc(FakeHTTP(post_responses=[_BadJsonResp()]))
        assert gc.find_stale() == []

    def test_collect_once_bad_json_does_not_raise(self):
        gc = _gc(FakeHTTP(post_responses=[_BadJsonResp()]))
        out = gc.collect_once()
        assert out["stale"] == 0 and out["aborted"] == 0


class TestFindStale:
    def test_returns_exec_ids_and_doc_ids(self):
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits(("doc1", {"execution_id": "e1", "started_at": 100}),
                                 ("doc2", {"execution_id": "e2"})))
            ]
        )
        stale = _gc(http).find_stale(now=10_000)
        assert [s["execution_id"] for s in stale] == ["e1", "e2"]
        assert [s["doc_id"] for s in stale] == ["doc1", "doc2"]

    def test_query_uses_keyword_and_cutoff(self):
        http = FakeHTTP(post_responses=[_Resp(200, _hits())])
        _gc(http, stale_minutes=30).find_stale(now=10_000)
        must = http.posts[0][1]["query"]["bool"]["must"]
        status_should = must[0]["bool"]["should"]
        assert {"term": {"status": "EXECUTING"}} in status_should
        assert {"term": {"status.keyword": "EXECUTING"}} in status_should
        assert must[1]["range"]["started_at"]["lt"] == 10_000 - 30 * 60

    def test_nested_workflow_id_extracted(self):
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits(("d", {"execution_id": "e",
                                        "workflow": {"id": "wf-1"}})))
            ]
        )
        assert _gc(http).find_stale()[0]["workflow_id"] == "wf-1"

    def test_missing_index_returns_empty(self):
        assert _gc(FakeHTTP(post_responses=[_Resp(404)])).find_stale() == []

    def test_http_error_returns_empty(self):
        assert _gc(FakeHTTP(post_responses=[_Resp(500)])).find_stale() == []

    def test_transport_error_returns_empty(self):
        class Boom(FakeHTTP):
            def post(self, url, **kw):
                raise ConnectionError("os down")

        assert _gc(Boom()).find_stale() == []


class TestConditionalTransition:
    def test_updated_result_returns_true(self):
        http = FakeHTTP(post_responses=[_updated()])
        assert _gc(http)._transition("d1", "EXECUTING", "TIMED_OUT") is True
        url, body = http.posts[0]
        assert f"/{EXECUTION_INDEX}/_update/d1" in url
        params = body["script"]["params"]
        assert params["expected"] == "EXECUTING"
        assert params["next"] == "TIMED_OUT"

    def test_noop_result_returns_false(self):
        """Doc moved on externally (late FINISHED) → transition is a noop."""
        http = FakeHTTP(post_responses=[_Resp(200, {"result": "noop"})])
        assert _gc(http)._transition("d1", "EXECUTING", "TIMED_OUT") is False

    def test_http_error_returns_false(self):
        assert _gc(FakeHTTP(post_responses=[_Resp(500)]))._transition(
            "d", "EXECUTING", "TIMED_OUT") is False


class TestApiAbort:
    def test_2xx_is_ok(self):
        assert _gc(FakeHTTP(delete_codes=[200]))._api_abort("e1") == "ok"

    def test_404_is_gone(self):
        assert _gc(FakeHTTP(delete_codes=[404]))._api_abort("e1") == "gone"

    def test_5xx_is_failed(self):
        assert _gc(FakeHTTP(delete_codes=[500]))._api_abort("e1") == "failed"

    def test_transport_error_is_failed(self):
        class Boom(FakeHTTP):
            def delete(self, url, **kw):
                raise ConnectionError("down")

        assert _gc(Boom())._api_abort("e1") == "failed"


class TestCollectOnceStateMachine:
    def test_abort_gone_terminates_aborted(self):
        """Stale + backend already forgot it → TIMED_OUT→ABORTED, audit set."""
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits()),                    # oldest EXECUTING scan
                _Resp(200, _hits(("d", {"execution_id": "e1"}))),  # stale scan
                _updated(),                             # → TIMED_OUT
                _updated(),                             # → ABORTED
                _Resp(200, _hits()),                    # CANCELLING scan
            ],
            delete_codes=[404],
        )
        gc = _gc(http)
        out = gc.collect_once(now=99_999)
        assert out["stale"] == 1 and out["timed_out"] == 1
        assert out["aborted"] == 1 and out["api_failed"] == 0
        assert gc.metrics.stuck_total == 1
        assert gc.metrics.transitions["TIMED_OUT"] == 1
        assert gc.metrics.transitions["ABORTED"] == 1

    def test_abort_ok_confirmed_via_backend(self):
        """Abort accepted → CANCELLING; backend GET 404 → ABORTED."""
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits()),
                _Resp(200, _hits(("d", {"execution_id": "e1"}))),
                _updated(),                              # TIMED_OUT
                _updated(),                              # CANCELLING
                _Resp(200, _hits(("d", {"execution_id": "e1"}))),  # CANCELLING scan
                _updated(),                              # ABORTED
            ],
            delete_codes=[200],
            get_responses=[_Resp(404)],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["cancelling"] == 1 and out["aborted"] == 1

    def test_abort_failure_stays_timed_out(self):
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits()),
                _Resp(200, _hits(("d", {"execution_id": "e1"}))),
                _updated(),                       # TIMED_OUT only
                _Resp(200, _hits()),              # CANCELLING scan
            ],
            delete_codes=[500],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["api_failed"] == 1 and out["aborted"] == 0

    def test_cancelling_retries_with_attempt_counter(self):
        """Backend still reports running → stays CANCELLING, attempts++."""
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits()),              # oldest
                _Resp(200, _hits()),              # stale
                _Resp(200, _hits(("d", {"execution_id": "e1",
                                        "confirm_attempts": 1}))),
                _updated(),                       # attempts bump
            ],
            get_responses=[_Resp(200, {"status": "EXECUTING"})],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["aborted"] == 0
        body = http.posts[-1][1]
        assert body["script"]["params"]["fields"]["confirm_attempts"] == 2

    def test_cancelling_forced_abort_at_max_attempts(self):
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits()),
                _Resp(200, _hits()),
                _Resp(200, _hits(("d", {"execution_id": "e1",
                                        "confirm_attempts": MAX_CONFIRM_ATTEMPTS}))),
                _updated(),                       # forced ABORTED
            ],
            get_responses=[_Resp(200, {"status": "EXECUTING"})],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["aborted"] == 1
        assert http.posts[-1][1]["script"]["params"]["fields"]["forced"] is True

    def test_late_finished_not_clobbered(self):
        """Transition noop (doc went FINISHED) → nothing else happens."""
        http = FakeHTTP(
            post_responses=[
                _Resp(200, _hits()),
                _Resp(200, _hits(("d", {"execution_id": "e1"}))),
                _Resp(200, {"result": "noop"}),   # TIMED_OUT transition noop
                _Resp(200, _hits()),              # CANCELLING scan
            ],
        )
        out = _gc(http).collect_once(now=99_999)
        assert out["timed_out"] == 0 and out["aborted"] == 0
        assert http.deletes == []  # abort never issued for a finished doc

    def test_no_stale_is_noop_but_gauge_set(self):
        http = FakeHTTP(post_responses=[
            _Resp(200, _hits(("f", {"execution_id": "e",
                                    "started_at": 99_000}))),
            _Resp(200, _hits()),
            _Resp(200, _hits()),
        ])
        gc = _gc(http)
        out = gc.collect_once(now=99_999)
        assert out["stale"] == 0 and out["aborted"] == 0
        assert http.deletes == []
        assert gc.metrics.oldest_executing_seconds == 999

    def test_fresh_executing_not_collected(self):
        http = FakeHTTP(post_responses=[
            _Resp(200, _hits()), _Resp(200, _hits()), _Resp(200, _hits()),
        ])
        out = _gc(http, stale_minutes=30).collect_once(now=3600)
        must = http.posts[1][1]["query"]["bool"]["must"]
        assert must[1]["range"]["started_at"]["lt"] == 3600 - 1800
        assert out["stale"] == 0
