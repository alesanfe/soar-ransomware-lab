#!/usr/bin/env python3
"""Mutation-hardening round 4 — killable survivors across the ingestion
pipeline. Exact contracts: message dicts, boundary conditions, call args,
resolved defaults and log output."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from soar_lab.interfaces.api.middleware.body_limit import BodyLimitMiddleware
from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
    PreAuthRateLimitMiddleware,
)
from soar_lab.interfaces.api.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from soar_lab.infrastructure.messaging.shuffle_forward import (
    DestinationPolicyError,
    _validate_target,
    make_shuffle_forward,
)
from soar_lab.infrastructure.messaging.worker_lease import WorkerLease
from soar_lab.resilience.bulkhead import AsyncBulkhead, Bulkhead, BulkheadFullError
from soar_lab.domain.statistics import summary_stats
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer, _extract_mttr
from soar_lab.domain.services.cortex_job_classifier import classify_job, summarize_jobs
from soar_lab.security import webhook_signing as ws
from soar_lab.security.redaction import redact_text, redact_url


# ── body_limit ───────────────────────────────────────────────────────────────


class TestBodyLimitStreamContracts:
    def _scope(self, **kw):
        s = {
            "type": "http",
            "method": "POST",
            "path": "/x",
            "headers": [],
            "client": ("10.0.0.1", 1),
        }
        s.update(kw)
        return s

    async def _drive(self, mw, scope, msgs, app):
        sent = []
        it = iter(msgs)

        async def receive():
            return next(it, {"type": "http.disconnect"})

        async def send(m):
            sent.append(m)

        await mw(scope, receive, send)
        return sent

    async def test_missing_path_key_uses_default(self):
        """``scope.get("path", "")`` — mutants dropping the default crash."""
        seen = {}

        async def app(scope, receive, send):
            seen["called"] = True
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app)
        scope = self._scope()
        del scope["path"]
        await self._drive(mw, scope, [], app)
        assert seen["called"] is True

    async def test_missing_headers_key_uses_default(self):
        """``scope.get("headers", [])`` — mutants dropping the default crash."""
        seen = {}

        async def app(scope, receive, send):
            seen["called"] = True
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app)
        scope = self._scope()
        del scope["headers"]
        await self._drive(mw, scope, [], app)
        assert seen["called"] is True

    async def test_streamed_exact_limit_not_truncated(self, caplog):
        """Boundary: received == limit must pass (kills >=, +1 offsets)."""
        body = b"1234"
        seen = {}

        async def app(scope, receive, send):
            seen["msg"] = await receive()
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app, default_max_bytes=4)
        msgs = [{"type": "http.request", "body": body, "more_body": False}]
        with caplog.at_level(logging.WARNING):
            await self._drive(mw, self._scope(), msgs, app)
        assert seen["msg"]["body"] == body
        assert "exceeded" not in caplog.text

    async def test_streamed_one_over_exact_message(self, caplog):
        """Exact truncated-message contract (kills XX'd keys)."""
        seen = {}

        async def app(scope, receive, send):
            seen["msg"] = await receive()
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app, default_max_bytes=4)
        msgs = [{"type": "http.request", "body": b"12345", "more_body": False}]
        with caplog.at_level(logging.WARNING):
            await self._drive(mw, self._scope(), msgs, app)
        assert seen["msg"] == {
            "type": "http.request",
            "body": b"",
            "more_body": False,
            "_over_limit": True,
        }
        assert "request body exceeded 4 bytes mid-stream on /x" in caplog.text

    async def test_streamed_multi_chunk_accumulates(self, caplog):
        """received += must accumulate (kills received = len(chunk))."""
        async def app(scope, receive, send):
            await receive()
            await receive()
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app, default_max_bytes=8)
        msgs = [
            {"type": "http.request", "body": b"12345", "more_body": True},
            {"type": "http.request", "body": b"6789", "more_body": False},
        ]
        with caplog.at_level(logging.WARNING):
            await self._drive(mw, self._scope(), msgs, app)
        assert "exceeded 8 bytes" in caplog.text

    async def test_read_timeout_boundary(self, caplog):
        """elapsed == _READ_TIMEOUT_S must pass (kills >=)."""
        async def app(scope, receive, send):
            seen = await receive()
            assert seen["body"] == b"ab"
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app, default_max_bytes=10)
        msgs = [{"type": "http.request", "body": b"ab", "more_body": False}]
        ticks = iter([0.0, 30.0, 30.0, 30.0])
        with patch("time.monotonic", side_effect=lambda: next(ticks)):
            with caplog.at_level(logging.WARNING):
                await self._drive(mw, self._scope(), msgs, app)
        assert "exceeded" not in caplog.text

    async def test_normal_body_no_warning(self, caplog):
        """over_limit starts False (kills hit=True / pop default True)."""
        async def app(scope, receive, send):
            await receive()
            await PlainTextResponse("ok")(scope, receive, send)

        mw = BodyLimitMiddleware(app, default_max_bytes=100)
        msgs = [{"type": "http.request", "body": b"ok", "more_body": False}]
        with caplog.at_level(logging.WARNING):
            await self._drive(mw, self._scope(), msgs, app)
        assert "exceeded" not in caplog.text


# ── security_headers ─────────────────────────────────────────────────────────


class TestSecurityHeadersRound4:
    def _client(self):
        async def ok(request):
            return PlainTextResponse("x")

        app = Starlette(
            routes=[
                Route("/x", ok),
                Route("/auth/login", ok),
                Route("/docs", ok),
            ]
        )
        app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(app)

    def test_permissions_policy_full_value(self):
        h = self._client().get("/x").headers
        assert h["Permissions-Policy"] == (
            "accelerometer=(), autoplay=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
        )

    def test_auth_path_gets_no_store(self):
        r = self._client().get("/auth/login")
        assert r.headers["Cache-Control"] == "no-store"

    def test_docs_path_no_cache_control(self):
        r = self._client().get("/docs")
        assert "cache-control" not in r.headers


# ── preauth_rate_limit ───────────────────────────────────────────────────────


class TestPreAuthSweepBoundary:
    def test_stale_exactly_60s_evicted(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=2)
        t = 1000.0
        mw._last_sweep = t - 121
        mw._hits["old"] = deque([t - 60.0])
        mw._allow("new", t)
        assert "old" not in mw._hits

    def test_fresh_key_not_swept(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=2)
        t = 1000.0
        mw._last_sweep = t - 121
        mw._hits["fresh"] = deque([t])
        mw._allow("new", t)
        assert "fresh" in mw._hits

    def test_sweep_only_after_120s(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=2)
        t = 1000.0
        mw._last_sweep = t
        mw._hits["old"] = deque([t - 100])
        mw._allow("new", t + 119.9)
        assert "old" in mw._hits
        mw._last_sweep = t
        mw._allow("new", t + 120.1)
        assert "old" not in mw._hits  # sweep ran: 220s-old entry evicted


# ── shuffle_forward ──────────────────────────────────────────────────────────


class TestShuffleForwardRound4:
    def _cfg(self, **kw):
        vals = {
            "ALERT_INGEST_TARGET_URL": "http://shuffle:5001/wh",
            "ALERT_SIGNING_KEY": "s3cret",
        }
        vals.update(kw)
        return lambda k, d=None: vals.get(k, d)

    def test_host_allowlist_empty_hostname(self):
        with pytest.raises(DestinationPolicyError, match="host ''"):
            _validate_target("http://:8080/x", {"other"})

    def test_default_key_id_in_signed_envelope(self):
        captured = {}

        def fake_sign(env, key, *, key_id):
            captured["key_id"] = key_id
            return env

        client = MagicMock()
        client.post_json = AsyncMock(return_value=(200, {"execution_id": "e1"}))
        with patch(
            "soar_lab.infrastructure.messaging.shuffle_forward.sign_envelope",
            side_effect=fake_sign,
        ):
            fwd = make_shuffle_forward(self._cfg(), http_client=client)
            asyncio.run(fwd({"alert_id": "a1"}))
        assert captured["key_id"] == "api-forward-1"

    def test_forward_logs_target(self, caplog):
        client = MagicMock()
        client.post_json = AsyncMock(return_value=(200, {}))
        with caplog.at_level(logging.INFO, logger="soar_lab.infrastructure.messaging.shuffle_forward"):
            make_shuffle_forward(self._cfg(), http_client=client)
        assert "Admission worker forwards alerts to http://shuffle:5001/wh" in caplog.text

    def test_owned_client_recreated_after_close(self):
        client1 = MagicMock()
        client1.post_json = AsyncMock(return_value=(200, {}))
        client1.close = AsyncMock()
        client2 = MagicMock()
        client2.post_json = AsyncMock(return_value=(200, {}))
        client2.close = AsyncMock()
        with patch(
            "soar_lab.infrastructure.messaging.shuffle_forward.AioHTTPClient",
            side_effect=[client1, client2],
        ) as ctor:
            fwd = make_shuffle_forward(self._cfg())
            asyncio.run(fwd({"alert_id": "a"}))
            asyncio.run(fwd.aclose())
            asyncio.run(fwd({"alert_id": "b"}))
            assert ctor.call_count == 2
            assert client2.post_json.await_count == 1

    def test_aclose_idempotent(self):
        client1 = MagicMock()
        client1.post_json = AsyncMock(return_value=(200, {}))
        client1.close = AsyncMock()
        with patch(
            "soar_lab.infrastructure.messaging.shuffle_forward.AioHTTPClient",
            return_value=client1,
        ):
            fwd = make_shuffle_forward(self._cfg())
            asyncio.run(fwd({"alert_id": "a"}))
            asyncio.run(fwd.aclose())
            asyncio.run(fwd.aclose())
            assert client1.close.await_count == 1


# ── worker_lease ─────────────────────────────────────────────────────────────


class TestWorkerLeaseLogs:
    async def test_held_failure_logs_warning(self, caplog):
        client = MagicMock()
        client.eval = AsyncMock(side_effect=RuntimeError("redis boom"))
        lease = WorkerLease(client, "w1")
        with caplog.at_level(logging.WARNING):
            ok = await lease.held()
        assert ok is False
        assert "Worker lease check failed: redis boom" in caplog.text

    async def test_release_failure_logs_debug(self, caplog):
        client = MagicMock()
        client.eval = AsyncMock(side_effect=RuntimeError("bye"))
        lease = WorkerLease(client, "w1")
        with caplog.at_level(logging.DEBUG):
            await lease.release()
        assert "Worker lease release failed: bye" in caplog.text

    async def test_held_res0_false_res1_true(self):
        client = MagicMock()
        client.eval = AsyncMock(return_value=0)
        lease = WorkerLease(client, "w1")
        assert await lease.held() is False
        client.eval = AsyncMock(return_value=1)
        assert await lease.held() is True
        assert lease.fence_token is None

    async def test_held_res2_fences(self):
        client = MagicMock()
        client.eval = AsyncMock(return_value=2)
        client.incr = AsyncMock(return_value=7)
        lease = WorkerLease(client, "w1")
        assert await lease.held() is True
        assert lease.fence_token == 7
        client.eval.assert_awaited()


# ── bulkhead ─────────────────────────────────────────────────────────────────


class TestBulkheadContracts:
    def test_full_raises_named_error(self):
        bh = Bulkhead("api", concurrent=1, queued=0, acquire_timeout=0.01)
        blocker = __import__("threading").Event()
        import threading

        t = threading.Thread(target=lambda: bh.run(blocker.wait))
        t.start()
        time.sleep(0.05)
        try:
            with pytest.raises(BulkheadFullError, match="api"):
                bh.run(lambda: None)
        finally:
            blocker.set()
            t.join()

    def test_queue_acquire_uses_timeout(self):
        bh = Bulkhead("b", concurrent=1, queued=1, acquire_timeout=5.0)
        bh._queue = MagicMock()
        bh._queue.acquire.return_value = False
        with pytest.raises(BulkheadFullError):
            bh.run(lambda: 1)
        bh._queue.acquire.assert_called_once_with(timeout=5.0)

    async def test_async_wait_for_uses_timeout(self):
        bh = AsyncBulkhead("a", concurrent=1, queued=1, acquire_timeout=3.0)
        sem = MagicMock()
        sem.acquire = AsyncMock(side_effect=asyncio.TimeoutError)
        bh._slots = MagicMock()  # non-None so _ensure() keeps our mock
        bh._queue = sem
        timeouts = []
        real_wait_for = asyncio.wait_for

        async def spy(coro, timeout=None):
            timeouts.append(timeout)
            return await real_wait_for(coro, timeout=timeout)

        with patch("asyncio.wait_for", side_effect=spy):
            with pytest.raises(BulkheadFullError, match="a"):
                await bh.run(AsyncMock())
        assert timeouts == [3.0]


# ── statistics / statistical_calculator ──────────────────────────────────────


class TestStatisticsContracts:
    def test_summary_stats_empty(self):
        r = summary_stats([])
        assert r["n"] == 0 and r["mean"] == 0.0
        assert r["p50"] == 0.0 and r["p99"] == 0.0

    def test_summary_stats_populated(self):
        r = summary_stats([1.0, 2.0, 3.0, 4.0])
        assert r["n"] == 4 and r["median"] == 2.5
        assert set(r) >= {"p50", "p90", "p95", "p99"}


class TestStatisticalCalculatorRound4:
    def test_percentile_rounding_exact(self):
        times = [float(i) for i in range(1, 101)]
        r = StatisticalCalculator.calculate_statistical_metrics(times)
        assert r["p90"] == 90.1
        assert r["p95"] == 95.05
        assert r["p99"] == 99.01
        assert r["mean"] == 50.5

    def test_health_score_two_decimals(self):
        r = StatisticalCalculator.calculate_health_score(33.333, 11.111, 5.0, 87.654)
        assert r["overall_score"] == 83.2
        assert r["components"]["cpu"] == 66.67
        assert r["status"] == "excellent"

    def test_health_score_critical_boundary(self):
        r = StatisticalCalculator.calculate_health_score(90, 90, 90, 0)
        assert r["overall_score"] == 9.0
        assert r["status"] == "critical"
        r2 = StatisticalCalculator.calculate_health_score(0, 0, 0, 0)
        assert r2["overall_score"] == 80.0 and r2["status"] == "excellent"

    def test_execution_times_only_started_keys(self):
        from datetime import datetime

        steps = {"STEP STARTED": [datetime(2024, 1, 1, 0, 0, 0)]}
        assert StatisticalCalculator.calculate_execution_times(steps) == []


# ── kpi_analyzer ─────────────────────────────────────────────────────────────


class TestKpiAnalyzerRound4:
    def test_avg_severity_two_decimals(self):
        metrics = [
            {"alert_type": "x", "severity": 4},
            {"alert_type": "x", "severity": 3},
            {"alert_type": "x", "severity": 3},
        ]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_severity"] == 3.33
        assert r["by_alert_type"]["x"]["count"] == 3

    def test_critical_rate_rounded(self):
        metrics = [{"alert_type": "x", "severity": 5}] + [
            {"alert_type": "x", "severity": 1}
        ] * 2
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["critical_rate"] == 33.33
        assert r["by_alert_type"]["x"]["critical_count"] == 1

    def test_mttr_window_boundary_included(self):
        metrics = [{"alert_type": "x", "mttr_seconds": 24 * 3600}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics, hours=24)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 86400.0

    def test_mttr_over_window_excluded(self):
        metrics = [{"alert_type": "x", "mttr_seconds": 24 * 3600 + 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics, hours=24)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 0

    def test_extract_mttr_variants(self):
        assert _extract_mttr(None) == 0.0
        assert _extract_mttr({}) == 0.0
        assert _extract_mttr({"message": "MTTR: 12.5s"}) == 12.5
        assert _extract_mttr("9") == 0.0
        assert _extract_mttr(9.0) == 9.0


# ── cortex_job_classifier ────────────────────────────────────────────────────


class TestCortexClassifierRound4:
    @pytest.mark.parametrize(
        "status",
        ["Waiting", "InProgress", "Running", "Started", "waiting", "inprogress"],
    )
    def test_pending_statuses_classified_unknown(self, status):
        # Infra hint in the message would misclassify if the status check
        # fell through — pending statuses must win (kills XX/case mutants).
        job = {"status": status, "statusMessage": "connection timeout"}
        assert classify_job(job) == "unknown"

    def test_two_jobs_same_slot_count(self):
        r = summarize_jobs(
            [
                {"status": "Success", "analyzerName": "a1"},
                {"status": "Success", "analyzerName": "a1"},
                {"status": "Failure", "analyzerName": "a1"},
            ]
        )
        assert r["by_category"]["success"] == 2
        assert r["by_category"]["analyzer_error"] == 1
        assert r["by_analyzer"]["a1"]["success"] == 2


# ── webhook_signing ──────────────────────────────────────────────────────────


class TestWebhookSigningRound4:
    SECRET = "s3cret-key"

    def _headers(self, *, now=None, key_id="k1", secret=None, body=b"hi"):
        return ws.sign_request(
            secret or self.SECRET,
            method="POST",
            path="/cb",
            body=body,
            key_id=key_id,
            now=now,
        )

    def test_sign_request_uses_now_param(self):
        h = self._headers(now=1700000123)
        assert h["X-SOAR-Timestamp"] == "1700000123"

    def test_sign_envelope_now_and_key_id(self):
        out = ws.sign_envelope({"a": 1}, self.SECRET, key_id="kid-9", now=1700000123)
        sec = out["security"]
        assert sec["timestamp"] == 1700000123
        assert sec["key_id"] == "kid-9"
        assert sec["alg"] == "v1"
        assert set(sec) == {
            "alg",
            "key_id",
            "timestamp",
            "nonce",
            "payload_sha256",
            "signature",
        }

    async def test_verify_request_replay_raises(self):
        store = ws.InMemoryNonceStore()
        h = self._headers()
        resolver = lambda kid: self.SECRET
        await ws.verify_request(
            resolver,
            method="POST",
            path="/cb",
            headers=h,
            body=b"hi",
            nonce_store=store,
        )
        with pytest.raises(ws.ReplayError, match="nonce already used"):
            await ws.verify_request(
                resolver,
                method="POST",
                path="/cb",
                headers=h,
                body=b"hi",
                nonce_store=store,
            )

    async def test_verify_request_claims_the_nonce(self):
        store = MagicMock()
        store.claim = AsyncMock(return_value=True)
        h = self._headers()
        await ws.verify_request(
            lambda kid: self.SECRET,
            method="POST",
            path="/cb",
            headers=h,
            body=b"hi",
            nonce_store=store,
        )
        store.claim.assert_awaited_once_with(h["X-SOAR-Nonce"])

    async def test_nonce_expired_boundary(self):
        store = ws.InMemoryNonceStore()
        now = time.time()
        store._nonces["old"] = now  # expires exactly now
        with patch("time.time", return_value=now):
            assert await store.claim("fresh", ttl_s=10) is True
        assert "old" not in store._nonces

    def test_verify_envelope_now_param(self):
        out = ws.sign_envelope({"a": 1}, self.SECRET, key_id="k", now=1700000000)
        r = ws.verify_envelope(out, lambda kid: self.SECRET, now=1700000050)
        assert r["key_id"] == "k"

    def test_envelope_stale_timestamp(self):
        out = ws.sign_envelope({"a": 1}, self.SECRET, key_id="k", now=1700000000)
        with pytest.raises(ws.SignatureError) as exc:
            ws.verify_envelope(out, lambda kid: self.SECRET, now=1700001000)
        assert exc.value.code == "SIGNATURE_STALE"

    async def test_signature_scheme_rpartition(self):
        """Sig with extra '=' — partition keeps scheme v1, sig hex breaks."""
        h = self._headers()
        h["X-SOAR-Signature"] = "v1=aa=bb"
        with pytest.raises(ws.SignatureError, match="signature mismatch"):
            await ws.verify_request(
                lambda kid: self.SECRET,
                method="POST",
                path="/cb",
                headers=h,
                body=b"hi",
            )

    def test_envelope_missing_fields(self):
        with pytest.raises(ws.SignatureError) as e1:
            ws.verify_envelope({}, lambda k: self.SECRET)
        assert e1.value.code == "SIGNATURE_MISSING"
        with pytest.raises(ws.SignatureError) as e2:
            ws.verify_envelope({"security": {"alg": "v2"}}, lambda k: self.SECRET)
        assert e2.value.code == "SIGNATURE_ALG"


# ── redaction ────────────────────────────────────────────────────────────────


class TestRedactionRound4:
    def test_secret_kv_exact(self):
        out = redact_text("token=abc123 other=1")
        assert "token=[redacted]" in out
        assert "abc123" not in out

    def test_control_chars_become_space(self):
        assert redact_text("a\x01b\x7fc") == "a b c"

    def test_query_params_redacted(self):
        out = redact_url("http://h/x?sig=deadbeef&k=2")
        assert out == "http://h/x?[redacted]"


# ── send_alert ───────────────────────────────────────────────────────────────


class TestSendAlertRound4:
    def _write_info(self, tmp_path: Path, data: dict, subdir="runtime/results"):
        p = tmp_path / subdir / "webhook_info.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
        return p

    def test_container_prefers_internal_url(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        self._write_info(
            tmp_path,
            {"webhook_url": "http://internal:1", "webhook_url_host": "http://host:2"},
        )
        monkeypatch.setattr(Path, "exists", lambda self: "/.dockerenv" in str(self) or str(self).endswith("webhook_info.json"))
        import soar_lab.infrastructure.messaging.send_alert as sa

        monkeypatch.setattr(sa, "WEBHOOK_INFO_PATHS", [])
        assert sa._default_webhook_url(tmp_path) == "http://internal:1"

    def test_host_prefers_host_url(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        self._write_info(
            tmp_path,
            {"webhook_url": "http://internal:1", "webhook_url_host": "http://host:2"},
        )
        real_exists = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            lambda self: False if str(self) == "/.dockerenv" else real_exists(self),
        )
        import soar_lab.infrastructure.messaging.send_alert as sa

        monkeypatch.setattr(sa, "WEBHOOK_INFO_PATHS", [])
        assert sa._default_webhook_url(tmp_path) == "http://host:2"

    def test_env_url_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SHUFFLE_WEBHOOK_URL", "http://env:9")
        import soar_lab.infrastructure.messaging.send_alert as sa

        assert sa._default_webhook_url(tmp_path) == "http://env:9"

    def test_fallback_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        import soar_lab.infrastructure.messaging.send_alert as sa

        monkeypatch.setattr(sa, "WEBHOOK_INFO_PATHS", [])
   