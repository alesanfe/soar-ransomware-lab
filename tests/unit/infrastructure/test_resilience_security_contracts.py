"""Exact-contract tests for the remaining hardened modules — kills the
mutation classes the behavioural suites leave alive: constructor defaults,
validation boundaries, exact strings, env resolution and numeric formulas.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


# ── Bulkhead ─────────────────────────────────────────────────────────────


class TestBulkheadContract:
    def test_sync_defaults(self):
        from soar_lab.resilience.bulkhead import Bulkhead

        b = Bulkhead("x")
        assert b.concurrent == 10
        assert b.queued == 50
        assert b.acquire_timeout == 5.0
        assert b.name == "x"

    def test_async_defaults(self):
        from soar_lab.resilience.bulkhead import AsyncBulkhead

        b = AsyncBulkhead("x")
        assert b._concurrent == 10
        assert b._queued == 50
        assert b.acquire_timeout == 5.0
        assert b.name == "x"

    @pytest.mark.parametrize(
        "kw",
        [
            {"concurrent": 0},
            {"concurrent": -1},
            {"queued": -1},
            {"acquire_timeout": 0},
            {"acquire_timeout": -0.5},
        ],
    )
    def test_each_param_validated_independently(self, kw):
        from soar_lab.resilience.bulkhead import AsyncBulkhead, Bulkhead

        for cls in (Bulkhead, AsyncBulkhead):
            with pytest.raises(ValueError) as e:
                cls("x", **kw)
            assert str(e.value) == (
                "concurrent >= 1, queued >= 0, acquire_timeout > 0 required"
            )

    def test_boundary_values_accepted(self):
        from soar_lab.resilience.bulkhead import AsyncBulkhead, Bulkhead

        Bulkhead("x", concurrent=1, queued=0, acquire_timeout=0.001)
        AsyncBulkhead("x", concurrent=1, queued=0, acquire_timeout=0.001)

    def test_full_error_name_and_message(self):
        from soar_lab.resilience.bulkhead import BulkheadFullError

        e = BulkheadFullError("cortex")
        assert e.name == "cortex"
        assert str(e) == "bulkhead 'cortex' saturated"

    @pytest.mark.asyncio
    async def test_async_saturation_raises_named_error(self):
        import asyncio

        from soar_lab.resilience.bulkhead import AsyncBulkhead, BulkheadFullError

        b = AsyncBulkhead("res", concurrent=1, queued=0, acquire_timeout=0.05)
        gate = asyncio.Event()

        async def hold():
            await gate.wait()

        task = asyncio.create_task(b.run(hold))
        await asyncio.sleep(0.01)  # let the first call take the slot
        with pytest.raises(BulkheadFullError) as e:
            await b.run(lambda: None)
        assert e.value.name == "res"
        gate.set()
        await task


# ── tls_config ───────────────────────────────────────────────────────────


class TestTlsConfigContract:
    def test_falsey_set_exact(self):
        from soar_lab.security.tls_config import FALSEY_ENV

        assert FALSEY_ENV == frozenset({"0", "false", "no", "off"})

    @pytest.mark.parametrize("val", ["0", "false", "no", "off", "FALSE", " Off "])
    def test_verify_tls_falsey_values(self, monkeypatch, val):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.setenv("MYSVC_VERIFY_TLS", val)
        assert verify_tls("mysvc") is False

    @pytest.mark.parametrize("val", ["1", "true", "yes", "typo", ""])
    def test_verify_tls_everything_else_true(self, monkeypatch, val):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.setenv("MYSVC_VERIFY_TLS", val)
        assert verify_tls("mysvc") is True

    def test_verify_tls_unset_defaults_true(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.delenv("MYSVC_VERIFY_TLS", raising=False)
        assert verify_tls("mysvc") is True
        assert verify_tls("mysvc", default=False) is False

    def test_verify_tls_var_name_derivation(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.setenv("SHUFFLE_BACKEND_VERIFY_TLS", "0")
        assert verify_tls("shuffle-backend") is False
        # Full var name ending in _VERIFY_TLS passes through unchanged.
        assert verify_tls("SHUFFLE_BACKEND_VERIFY_TLS") is False

    def test_ca_verify_prefers_bundle(self, monkeypatch):
        from soar_lab.security import tls_config

        paths_seen = []

        class FakePath:
            def __init__(self, p):
                self._p = p

            def exists(self):
                paths_seen.append(self._p)
                return str(self._p) == "/app/certs/ca-bundle.crt"

            def __str__(self):
                return str(self._p)

            def __truediv__(self, other):
                return FakePath(f"{self._p}/{other}")

            def resolve(self):
                return self

            @property
            def parents(self):
                return [FakePath("/x"), FakePath("/x"), FakePath("/x"), FakePath("/x"), FakePath("/x")]

        monkeypatch.setattr(tls_config, "Path", FakePath)
        assert tls_config.ca_verify() == "/app/certs/ca-bundle.crt"
        assert paths_seen[0] == "/app/certs/ca-bundle.crt"  # bundle checked first

    def test_ca_verify_falls_back_to_default(self, monkeypatch):
        from soar_lab.security import tls_config

        class FakePath:
            def __init__(self, p):
                self._p = p

            def exists(self):
                return False

            def __str__(self):
                return str(self._p)

            def __truediv__(self, other):
                return FakePath(f"{self._p}/{other}")

            def resolve(self):
                return self

            @property
            def parents(self):
                return [FakePath("/x")] * 5

        monkeypatch.setattr(tls_config, "Path", FakePath)
        assert tls_config.ca_verify() is True
        assert tls_config.ca_verify(default=False) is False


# ── redaction / safe_error ───────────────────────────────────────────────


class TestRedactionContract:
    def test_hook_path_replacement_exact(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("call /api/v1/hooks/webhook_abc123 done")
        assert "/api/v1/hooks/[redacted]" in out
        assert "webhook_abc123" not in out

    def test_bearer_replacement_exact(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("Authorization: Bearer abcdefgh12345")
        assert "abcdefgh12345" not in out
        assert "[redacted]" in out

    def test_hex_blob_replacement_exact(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("sha " + "a" * 40 + " end")
        assert "[redacted-hex]" in out
        assert "a" * 40 not in out

    def test_query_replacement_exact(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("GET /x?token=abc123")
        assert "?[redacted]" in out
        assert "token=abc123" not in out

    def test_secret_kv_keeps_key_name(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("token=supersecret")
        assert out.startswith("token")
        assert "[redacted]" in out
        assert "supersecret" not in out

    def test_max_len_boundary(self):
        from soar_lab.security.redaction import redact_text

        s = "x" * 10
        # len == max_len → NOT truncated (kills > vs >=)
        assert redact_text(s, max_len=10) == "x" * 10
        # len > max_len → truncated + ellipsis
        assert redact_text("x" * 11, max_len=10) == "x" * 10 + "…"

    def test_none_returns_empty(self):
        from soar_lab.security.redaction import redact_text

        assert redact_text(None) == ""


class TestSafeErrorContract:
    def test_none_exc_falls_back_to_lower_code(self):
        from soar_lab.security.redaction import safe_error

        out = safe_error(None, code="FORWARD_FAILED", retryable=True)
        assert out == {
            "code": "FORWARD_FAILED",
            "destination": "downstream",
            "retryable": True,
            "message": "forward_failed",  # code.lower(), not upper
        }

    def test_destination_overridable(self):
        from soar_lab.security.redaction import safe_error

        out = safe_error("boom", code="X", retryable=False, destination="shuffle")
        assert out["destination"] == "shuffle"
        assert out["retryable"] is False

    def test_message_truncated_160(self):
        from soar_lab.security.redaction import safe_error

        out = safe_error("e" * 500, code="X", retryable=True)
        assert len(out["message"]) <= 161


# ── PreAuthRateLimitMiddleware internals ─────────────────────────────────


class TestPreAuthContract:
    def _mw(self, **kw):
        from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
            PreAuthRateLimitMiddleware,
        )

        async def app(scope, receive, send):
            pass

        return PreAuthRateLimitMiddleware(app, **kw)

    def test_trusted_proxy_non_strict_normalization(self):
        import ipaddress

        # "10.1.2.3/8" has host bits set — only strict=False accepts it.
        mw = self._mw(trusted_proxies=["10.1.2.3/8"])
        assert ipaddress.ip_network("10.0.0.0/8") in mw._trusted

    def test_invalid_cidr_ignored(self):
        mw = self._mw(trusted_proxies=["not-a-cidr"])
        assert mw._trusted == []

    def test_xff_hop_cap_20(self):
        mw = self._mw()
        mw._trusted = [__import__("ipaddress").ip_network("10.0.0.0/8")]
        # `[:20]` keeps the 20 leftmost hops then walks right-to-left.
        # Untrusted hops at index 19 AND 20: under [:20] the walk starts at
        # "8.8.8.8"; under [:19] it falls to host; under [:21] "9.9.9.9" wins.
        hops = ["10.0.0.2"] * 19 + ["8.8.8.8", "9.9.9.9"]
        scope = {
            "client": ("10.0.0.1", 1),
            "headers": [(b"x-forwarded-for", ", ".join(hops).encode())],
        }
        assert mw._client_ip(scope) == "8.8.8.8"

    def test_sweep_removes_stale_keys(self):
        mw = self._mw()
        mw._hits["old"].append(1000.0)
        mw._last_sweep = 1000.0
        # >120s since last sweep → stale entries (>=60s old) purged.
        mw._allow("new", now=1121.0)
        assert "old" not in mw._hits

    def test_sweep_boundary_not_yet(self):
        mw = self._mw()
        mw._hits["old"].append(1000.0)
        mw._last_sweep = 1000.0
        # 120s exactly → `>` not `>=` → no sweep yet.
        mw._allow("new", now=1120.0)
        assert "old" in mw._hits
        assert mw._last_sweep == 1000.0

    def test_stale_boundary_60s(self):
        mw = self._mw()
        mw._hits["old"].append(1000.0)
        mw._last_sweep = 1000.0
        # hit is exactly 60s old at sweep time → `>=` purges it.
        mw._allow("new", now=1120.1)
        assert "old" not in mw._hits
        assert mw._last_sweep == 1120.1


# ── sanitization boundaries ──────────────────────────────────────────────


class TestSanitizationContract:
    def test_max_length_boundary(self):
        from soar_lab.security.sanitization import PayloadSanitizer

        s = PayloadSanitizer()
        assert s.sanitize_js("x" * 10, max_length=10) == "x" * 10
        out = s.sanitize_js("x" * 11, max_length=10)
        assert len(out) <= 11

    def test_encode_decode_roundtrip(self):
        from soar_lab.security.sanitization import PayloadSanitizer

        s = PayloadSanitizer()
        data = {"a": 1, "b": "x"}
        assert s.decode(s.encode(data)) == data


# ── statistical_calculator / kpi_analyzer / alert_generator ──────────────


class TestStatsContract:
    def test_percentiles_rounded_2(self):
        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        out = StatisticalCalculator.calculate_statistical_metrics([1.0, 2.0, 3.0])
        for k in ("p50", "p90", "p95", "p99"):
            assert out[k] == round(out[k], 2)

    def test_empty_returns_zeros(self):
        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        out = StatisticalCalculator.calculate_statistical_metrics([])
        assert out["p50"] == 0.0 and out["total_executions"] == 0

    def test_health_score_weights(self):
        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        out = StatisticalCalculator.calculate_health_score(
            cpu_percent=0, memory_percent=0, disk_percent=0, test_coverage=100
        )
        # 100*0.3 + 100*0.3 + 100*0.2 + 100*0.2 = 100
        assert out["overall_score"] == 100.0
        assert out["status"] == "excellent"
        out2 = StatisticalCalculator.calculate_health_score(100, 100, 100, 0)
        assert out2["overall_score"] == 0.0
        assert out2["status"] == "critical"


class TestKpiAnalyzerContract:
    def test_avg_severity_and_critical_rate(self):
        from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer

        metrics = [
            {"alert_type": "t", "severity": 3, "mttr_seconds": 10},
            {"alert_type": "t", "severity": 5, "mttr_seconds": 20},
        ]
        out = KPIAnalyzer.calculate_kpis_by_alert_type(metrics, hours=24)
        t = out["by_alert_type"]["t"]
        assert t["count"] == 2
        assert t["avg_severity"] == 4.0
        assert t["avg_mttr_seconds"] == 15.0
        assert t["critical_rate"] == round(t["critical_count"] / 2 * 100, 2)
        assert out["period_hours"] == 24

    def test_mttr_outside_window_excluded(self):
        from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer

        metrics = [{"alert_type": "t", "severity": 1, "mttr_seconds": 999999}]
        out = KPIAnalyzer.calculate_kpis_by_alert_type(metrics, hours=1)
        assert out["by_alert_type"]["t"]["avg_mttr_seconds"] == 0

    def test_extract_mttr_dict_message(self):
        from soar_lab.domain.services.kpi_analyzer import _extract_mttr

        assert _extract_mttr({"message": "MTTR: 42.5s"}) == 42.5
        assert _extract_mttr({"message": "no marker"}) == 0
        assert _extract_mttr({"other": 1}) == 0
        assert _extract_mttr(12.0) == 12.0
        assert _extract_mttr("x") == 0


class TestAlertGeneratorContract:
    def test_id_seq_wraps_at_10000(self):
        from soar_lab.domain.alert_generator import AlertGenerator

        g = AlertGenerator(seq_offset=9999)
        alert_id = g._id()
        # (9999 + 1) % 10000 = 0 → "0000", not "10000" (kills %10_000→%10001)
        assert alert_id.endswith("-0000")


# ── rate_limit stores: exact Redis pipeline args + memory sweep ───────────


class TestRedisSlidingWindowStore:
    @pytest.mark.asyncio
    async def test_record_pipeline_args(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            RedisSlidingWindowStore,
        )

        pipe = Mock()
        pipe.execute = AsyncMock(
            return_value=[0, True, 3, [(b"m", 111.0)], True]
        )
        client = Mock()
        client.pipeline = Mock(return_value=pipe)
        store = RedisSlidingWindowStore(client)
        count, oldest = await store.record("k1", now=1000.0, window_s=60.0)
        client.pipeline.assert_called_once_with(transaction=False)
        pipe.zremrangebyscore.assert_called_once_with(
            "ratelimit:k1", "-inf", 940.0
        )
        member_arg = pipe.zadd.call_args
        assert member_arg[0][0] == "ratelimit:k1"
        assert list(member_arg[0][1].values()) == [1000.0]
        pipe.zcard.assert_called_once_with("ratelimit:k1")
        pipe.zrange.assert_called_once_with(
            "ratelimit:k1", 0, 0, withscores=True
        )
        pipe.expire.assert_called_once_with("ratelimit:k1", 62)
        assert count == 3 and oldest == 111.0

    @pytest.mark.asyncio
    async def test_record_oldest_none_when_empty(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            RedisSlidingWindowStore,
        )

        pipe = Mock()
        pipe.execute = AsyncMock(return_value=[0, True, 1, [], True])
        client = Mock()
        client.pipeline = Mock(return_value=pipe)
        store = RedisSlidingWindowStore(client)
        count, oldest = await store.record("k", now=5.0, window_s=60.0)
        assert count == 1 and oldest is None


class TestInMemorySlidingWindowStore:
    @pytest.mark.asyncio
    async def test_sweep_boundary_and_stale_rule(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        s = InMemorySlidingWindowStore()
        s._hits["old"].append(100.0)
        s._last_sweep = 100.0
        # now - last_sweep = 120 = 2*60 exactly → `>` not `>=` → no sweep.
        await s.record("k", now=220.0, window_s=60.0)
        assert "old" in s._hits
        # now > 2*window → sweep; stale hit age 120.1 >= window → purged.
        await s.record("k", now=220.1, window_s=60.0)
        assert "old" not in s._hits

    @pytest.mark.asyncio
    async def test_stale_boundary_exact_window(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        s = InMemorySlidingWindowStore()
        s._hits["old"].append(100.0)
        s._last_sweep = 39.0  # 161 - 39 = 122 > 120 → sweep happens
        # age = 161 - 100 = 61 >= 60 → purge (kills `>=`→`>`).
        await s.record("k", now=161.0, window_s=60.0)
        assert "old" not in s._hits

    @pytest.mark.asyncio
    async def test_fresh_key_survives_sweep(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        s = InMemorySlidingWindowStore()
        s._hits["a"].append(265.0)
        s._last_sweep = 200.0
        # Sweep fires (321-200 > 2*60): "a" is 56s old < window → kept.
        # `now + w[-1]` mutant marks every key stale and drops it.
        await s.record("other", now=321.0, window_s=60.0)
        assert "a" in s._hits

    @pytest.mark.asyncio
    async def test_first_hit_during_sweep_is_kept(self):
        """Regression: append-before-sweep — a brand-new key's hit used to
        be discarded when it coincided with a sweep (empty deque was
        flagged stale, popped, then appended to the orphaned deque)."""
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        s = InMemorySlidingWindowStore()
        s._last_sweep = 0.0  # sweep-eligible
        count, _ = await s.record("new", now=500.0, window_s=60.0)
        assert count == 1
        assert "new" in s._hits and s._hits["new"][-1] == 500.0


class TestRetryJitterContract:
    def test_zero_jitter_factor_deterministic(self, monkeypatch):
        from soar_lab.resilience.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            base_delay=2.0,
            jitter_factor=0.0,
        )
        monkeypatch.setattr(
            "soar_lab.resilience.retry.random.uniform",
            Mock(side_effect=AssertionError("jitter called at factor 0")),
        )
        # `jitter_factor > 0` skips jitter entirely at 0 (kills `>=`).
        assert policy._jittered_delay(0) == 2.0
        assert policy._jittered_delay(2) == 8.0


class TestNonceStoreBoundary:
    @pytest.mark.asyncio
    async def test_expired_at_exact_ttl_reclaimed(self, monkeypatch):
        from soar_lab.security import webhook_signing as ws

        store = ws.InMemoryNonceStore()
        monkeypatch.setattr(ws.time, "time", lambda: 1000.0)
        assert await store.claim("n1", ttl_s=60) is True
        # At expiry == now, `t <= now` purges → reclaim succeeds;
        # `<` would keep it → False.
        monkeypatch.setattr(ws.time, "time", lambda: 1060.0)
        assert await store.claim("n1", ttl_s=60) is True

    @pytest.mark.asyncio
    async def test_explicit_now_honored(self):
        import soar_lab.security.webhook_signing as ws

        body = b"{}"
        # explicit now within window must be used (not time.time()).
        sig = "v1=" + "0" * 64
        csha = ws.body_sha256(body)
        out = ws._verify_common(
            lambda k: "s",
            method="POST",
            path="/x",
            timestamp="500",
            nonce="n",
            content_sha=csha,
            signature=sig,
            body=body,
            nonce_store=None,
            skew_s=300,
            now=600.0,  # |600-500| = 100 < 300 → passes under real now
        )
        assert out["now"] == 600.0


class TestKpiZeroRates:
    def test_no_criticals_gives_zero_rate(self):
        from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer

        metrics = [{"alert_type": "t", "severity": 1, "mttr_seconds": 5}]
        out = KPIAnalyzer.calculate_kpis_by_alert_type(metrics, hours=24)
        t = out["by_alert_type"]["t"]
        # `else 0` — a non-critical alert type reports 0, not 1.
        assert t["critical_rate"] == 0
        assert t["avg_severity"] == 1.0


class TestExecutionTimesContract:
    def test_started_passed_pairs_delta(self):
        from datetime import datetime

        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        steps = {
            "Step1 STARTED": [datetime(2025, 1, 1, 0, 0, 0)],
            "Step1 PASSED": [datetime(2025, 1, 1, 0, 1, 0)],
        }
        out = StatisticalCalculator.calculate_execution_times(steps)
        assert out == [60.0]

    def test_negative_delta_filtered(self):
        from datetime import datetime

        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        steps = {
            "Step1 STARTED": [datetime(2025, 1, 1, 0, 1, 0)],
            "Step1 PASSED": [datetime(2025, 1, 1, 0, 0, 0)],  # before start
        }
        # `delta > 0` filter — negative pair must be dropped.
        assert StatisticalCalculator.calculate_execution_times(steps) == []

    def test_alert_containment_pairing(self):
        from datetime import datetime

        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        steps = {
            "Alert received": [datetime(2025, 1, 1, 0, 0, 0)],
            "Containment executed": [datetime(2025, 1, 1, 0, 2, 0)],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == [120.0]
