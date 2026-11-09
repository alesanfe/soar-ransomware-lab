"""Prometheus scrape endpoint: queue-metric omission and failure paths."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.routes_metrics import register_metrics_route


def _app(**state) -> FastAPI:
    app = FastAPI()
    for k, v in state.items():
        setattr(app.state, k, v)
    register_metrics_route(app)
    return app


class _Queue:
    def __init__(self, metrics_result=None, raises=False):
        self._m = metrics_result or {}
        self._raises = raises

    async def metrics(self, group=None):
        if self._raises:
            raise ConnectionError("redis gone")
        return dict(self._m)


class _Admission:
    def __init__(self, queue):
        self.queue = queue


class TestScrape:
    def test_no_queue_reports_unavailable(self):
        resp = TestClient(_app()).get("/metrics")
        assert resp.status_code == 200
        assert "soar_queue_available 0" in resp.text
        # queue-specific gauges absent entirely (None values are skipped)
        assert "soar_queue_depth" not in resp.text

    def test_queue_metrics_failure_skips_gauges(self):
        app = _app(admission_service=_Admission(_Queue(raises=True)))
        resp = TestClient(app).get("/metrics")
        assert resp.status_code == 200
        assert "soar_queue_available 1" in resp.text
        assert "soar_queue_depth" not in resp.text  # m={} → all None → skipped

    def test_full_queue_metrics_exposed(self):
        m = {"queue_depth": 5, "pending": 2, "consumer_lag": 1, "dlq_size": 3}
        app = _app(admission_service=_Admission(_Queue(metrics_result=m)))
        resp = TestClient(app).get("/metrics")
        assert "soar_queue_depth 5" in resp.text
        assert "soar_queue_pending 2" in resp.text
        assert "soar_queue_dlq_size 3" in resp.text

    def test_worker_stats_and_error_labels(self):
        class Stats:
            processed_total = 10
            forwarded_total = 8
            retried_total = 1
            dead_total = 1
            forward_seconds_total = 2.5
            inflight = 0
            errors = {'HTTP 503 "upstream"': 2}

        app = _app(admission_worker_stats=Stats())
        resp = TestClient(app).get("/metrics")
        assert "soar_admission_processed_total 10" in resp.text
        # label rendered with sanitized error fingerprint
        assert 'error="HTTP 503' in resp.text
        assert "soar_admission_forward_errors_total" in resp.text
