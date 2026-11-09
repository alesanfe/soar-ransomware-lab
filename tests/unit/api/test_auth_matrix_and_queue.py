"""AUTH-001/002 + QUEUE-001..006 + IDEMP-001 + VAL-001 + LOG-001 tests.

The auth matrix enumerates every registered route and asserts the
default-deny posture: only the explicit public whitelist may be reached
without ``require_api_auth``. The table is printed in markdown form so
it can be exported verbatim into the TFM (AUTH-002).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from soar_lab.interfaces.api.main import create_app


def _app() -> Any:
    cp = Mock()
    cp.get.side_effect = lambda key, default=None: {
        "API_REQUIRE_AUTH": "true",
        "API_DOCS_ENABLED": "true",
        "CORS_ORIGINS": ["https://soar.local"],
        "DOCS_DIR": "/nonexistent",
    }.get(key, default)
    cp.get_service_urls.return_value = {}
    auth = Mock()
    auth.verify_jwt_token.return_value = {"user": "admin", "role": "admin"}
    return create_app(
        config_provider=cp,
        auth_service=auth,
        system_metrics=Mock(),
        health_service=Mock(),
        analytics_service=Mock(),
        backup_service=Mock(),
        test_service=Mock(),
        storage=Mock(),
        path_service=Mock(),
        log_reader=Mock(),
    )


# Public whitelist — everything else MUST require auth (AUTH-001).
PUBLIC_PATH_PREFIXES = (
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/",
    "/api/v1/auth/",
    "/static",
)


def _route_has_auth(route: Any) -> bool:
    deps = list(getattr(route, "dependencies", []) or [])
    deps += list(getattr(getattr(route, "dependent", None), "dependencies", []) or [])
    for dep in deps:
        call = getattr(dep, "call", None) or dep
        name = getattr(call, "__name__", "")
        if name == "require_api_auth":
            return True
    return False


def _is_public(path: str) -> bool:
    from soar_lab.interfaces.api.auth import DefaultDenyAuthMiddleware

    return path == "/" or path.startswith(
        PUBLIC_PATH_PREFIXES + DefaultDenyAuthMiddleware.PUBLIC_PREFIXES
    )


def _has_default_deny_middleware(app: Any) -> bool:
    from soar_lab.interfaces.api.auth import DefaultDenyAuthMiddleware

    return any(m.cls is DefaultDenyAuthMiddleware for m in app.user_middleware)


class TestAuthEndpointMatrix:
    def test_default_deny_middleware_covers_every_route(self) -> None:
        """AUTH-001/002: every non-whitelisted route is covered either by
        a per-route ``Depends(require_api_auth)`` or by the default-deny
        middleware. Emits the exportable matrix for the TFM."""
        app = _app()
        middleware = _has_default_deny_middleware(app)
        matrix: list[tuple[str, str, bool]] = []
        uncovered: list[str] = []
        for route in app.routes:
            path = getattr(route, "path", "")
            methods = sorted(getattr(route, "methods", []) or {"WS"})
            if not path or path.startswith("/openapi"):
                continue
            public = _is_public(path)
            covered = (
                public
                or _route_has_auth(route)
                or path.startswith("/ws")  # WS scope: one-time ticket gate
                or middleware
            )
            for m in methods:
                matrix.append((m, path, covered))
            if not covered:
                uncovered.append(f"{methods} {path}")

        lines = ["| Method | Endpoint | Auth |", "|---|---|---|"]
        lines += [f"| {m} | `{p}` | {'✅' if a else '❌ OPEN'} |" for m, p, a in matrix]
        print("\n" + "\n".join(lines[:70]))

        assert middleware, "DefaultDenyAuthMiddleware not registered"
        assert not uncovered, f"Unauthenticated non-public routes: {uncovered}"

    def test_middleware_denies_unauthenticated_request(self) -> None:
        """Functional: an unauthenticated GET to a non-whitelisted route
        gets 401 from the middleware, not just from a route dep."""
        from fastapi.testclient import TestClient

        client = TestClient(_app())
        resp = client.get("/analytics/kpis")
        assert resp.status_code == 401

        resp2 = client.get("/health")
        assert resp2.status_code != 401

    def test_public_whitelist_still_reachable(self) -> None:
        paths = {getattr(r, "path", "") for r in _app().routes}
        assert "/health" in paths
        assert any(p.startswith("/api/v1/alerts") for p in paths)
        assert "/api/v1/queue/dlq" in paths
        assert "/api/v1/queue/metrics" in paths


# ---------------------------------------------------------------------------
# IDEMP-001: atomic SET-NX idempotency
# ---------------------------------------------------------------------------


class _FakeStore:
    """In-memory AdmissionStore with a REAL atomic try_bind_key (like SET NX)."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.keys: dict[str, str] = {}
        self.bind_calls = 0

    async def create(self, record):
        self.records[record["admission_id"]] = record

    async def update(self, aid, fields):
        self.records[aid].update(fields)

    async def get(self, aid):
        return self.records.get(aid)

    async def find_by_key(self, k):
        return self.keys.get(k)

    async def bind_key(self, k, aid):
        self.keys.setdefault(k, aid)

    async def try_bind_key(self, k, aid):
        self.bind_calls += 1
        if k in self.keys:
            return self.keys[k]
        self.keys[k] = aid
        return None

    async def unbind_key(self, k, aid):
        if self.keys.get(k) == aid:
            del self.keys[k]


class _FakeQueue:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def enqueue(self, e):
        self.events.append(e)
        return f"e-{len(self.events)}"

    async def depth(self):
        return len(self.events)


class TestAtomicIdempotency:
    @pytest.mark.asyncio
    async def test_concurrent_same_key_enqueues_once(self) -> None:
        """Two racing admits with the same key: ONE enqueue wins the NX
        claim; the loser gets the winner's admission back."""
        from soar_lab.application.use_cases.alert_admission import AlertAdmissionUseCase

        store, queue = _FakeStore(), _FakeQueue()
        uc = AlertAdmissionUseCase(queue=queue, store=store)

        r1, r2 = await asyncio.gather(
            uc.admit({"title": "a"}, idempotency_key="k1"),
            uc.admit({"title": "b"}, idempotency_key="k1"),
        )
        assert len(queue.events) == 1
        assert r1["admission_id"] == r2["admission_id"]

    @pytest.mark.asyncio
    async def test_failed_enqueue_unbinds_key(self) -> None:
        """Compensation: if enqueue dies after winning NX, the key is
        released so a retry is not stuck to a phantom admission."""
        from soar_lab.application.use_cases.alert_admission import AlertAdmissionUseCase

        store, queue = _FakeStore(), _FakeQueue()

        async def boom(_):
            raise RuntimeError("redis down")

        queue.enqueue = boom
        uc = AlertAdmissionUseCase(queue=queue, store=store)
        with pytest.raises(RuntimeError):
            await uc.admit({"title": "x"}, idempotency_key="k2")
        assert "k2" not in store.keys


# ---------------------------------------------------------------------------
# QUEUE-001..006: streams queue behaviour (fakeredis-free — stub client)
# ---------------------------------------------------------------------------


class TestQueueHardening:
    def test_enqueue_uses_bounded_maxlen(self) -> None:
        """QUEUE-004: XADD must carry MAXLEN ~ — an unbounded stream is a
        memory leak waiting for a burst."""
        from soar_lab.infrastructure.messaging.redis_streams_queue import (
            RedisStreamsQueue,
        )

        client = Mock()
        client.xadd = AsyncMock(return_value="1-1")
        q = RedisStreamsQueue(client, maxlen=1000)
        asyncio.run(q.enqueue({"a": 1}))
        kwargs = client.xadd.call_args.kwargs
        assert kwargs["maxlen"] == 1000
        assert kwargs["approximate"] is True

    @pytest.mark.asyncio
    async def test_poison_entry_goes_to_dlq_and_acked(self) -> None:
        """QUEUE-001: an undecodable entry is dead-lettered + acked instead
        of sitting pending forever."""
        from soar_lab.infrastructure.messaging.redis_streams_queue import (
            RedisStreamsQueue,
        )

        client = Mock()
        client.xreadgroup = AsyncMock(
            return_value=[(b"soar:admissions", [(b"1-1", {b"payload": b"{broken"})])]
        )
        client.xadd = AsyncMock(return_value="d-1")
        client.xack = AsyncMock()
        client.xgroup_create = AsyncMock(side_effect=Exception("BUSYGROUP"))
        q = RedisStreamsQueue(client)

        out = await q.read("g", "c", 10, 0)
        assert out == []
        client.xadd.assert_awaited_once()
        assert client.xadd.call_args.args[0] == "soar:admissions:dlq"
        client.xack.assert_awaited_once_with("soar:admissions", "g", b"1-1")

    @pytest.mark.asyncio
    async def test_dlq_lifecycle_list_redrive_purge(self) -> None:
        """QUEUE-002: list → redrive → purge the DLQ."""
        import json as _json

        from soar_lab.infrastructure.messaging.redis_streams_queue import (
            RedisStreamsQueue,
        )

        payload = _json.dumps({"admission_id": "a1", "attempts": 5})
        client = Mock()
        client.xadd = AsyncMock(return_value="n-1")
        client.xdel = AsyncMock()
        client.xtrim = AsyncMock()
        client.xrange = AsyncMock(
            return_value=[(b"0-1", {b"payload": payload.encode(), b"reason": b"dead"})]
        )
        client.xlen = AsyncMock(return_value=1)
        q = RedisStreamsQueue(client)

        entries = await q.dlq_list()
        assert entries[0]["reason"] == "dead"
        assert await q.dlq_redrive("0-1") is True
        # redrive resets the retry budget
        requeued = _json.loads(client.xadd.call_args.args[1]["payload"])
        assert requeued["attempts"] == 0
        client.xdel.assert_awaited_once()
        assert await q.dlq_purge() == 1
        client.xtrim.assert_awaited_once()


class TestWorkerBackoff:
    def test_backoff_schedule_is_exponential_with_jitter(self) -> None:
        """QUEUE-003: delay ∈ [0, base*2**(n-1)] capped at retry_cap."""
        from soar_lab.infrastructure.messaging.admission_worker import AdmissionWorker

        w = AdmissionWorker(queue=Mock(), store=Mock(), forward=AsyncMock())
        for _ in range(50):
            assert 0 <= w._retry_delay(1) <= 1.0
            assert 0 <= w._retry_delay(2) <= 2.0
            assert 0 <= w._retry_delay(6) <= 32.0
            assert 0 <= w._retry_delay(99) <= 32.0

    @pytest.mark.asyncio
    async def test_retry_sleeps_before_forward(self, monkeypatch) -> None:
        from soar_lab.infrastructure.messaging.admission_worker import AdmissionWorker

        slept: list[float] = []

        async def fake_sleep(d):
            slept.append(d)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        store, queue = Mock(), Mock()
        store.update = AsyncMock()
        queue.ack, queue.enqueue = AsyncMock(), AsyncMock()
        w = AdmissionWorker(queue=queue, store=store, forward=AsyncMock(return_value={"ok": False}))
        await w._process("e1", {"admission_id": "a", "attempts": 3, "alert": {}})
        assert len(slept) == 1
        assert 0 <= slept[0] <= 8.0  # 2^(3-1)=4 * base=1 → cap 4


# ---------------------------------------------------------------------------
# VAL-001 + LOG-001
# ---------------------------------------------------------------------------


class TestAlertSchema:
    def test_valid_simulator_alert_passes(self) -> None:
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        alert = AlertIngestSchema.model_validate(
            {
                "title": "Ransomware detected",
                "severity": 3,
                "hash": "e" * 64,
                "hostname": "ws-01",
                "mitre_techniques": ["T1486"],
                "extra_unknown_field": {"nested": True},
            }
        )
        assert alert.severity == 3

    @pytest.mark.parametrize(
        "bad",
        [
            {"severity": 9},
            {"severity": "x" * 40},
            {"hash": "not-a-hash"},
            {"alert_id": "x" * 200},
            {"mitre_techniques": "T1486"},  # must be a list
        ],
    )
    def test_invalid_alerts_rejected(self, bad) -> None:
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        with pytest.raises(Exception):
            AlertIngestSchema.model_validate(bad)


class TestSecretRedactor:
    @pytest.mark.parametrize(
        "raw, forbidden",
        [
            ("Bearer abc.def.ghi", "abc.def.ghi"),
            ("token=eyJhbGciOi.eyJzdWIiOiJ4.SflKxwRJSMeKKF2", "eyJhbGciOi"),
            ("api_key: supersecret123", "supersecret123"),
            ("password=hunter2 failed", "hunter2"),
            ("Authorization=Basic QWxhZGRpbjpvcGVu", "QWxhZGRpbjpvcGVu"),
            ("AKIAIOSFODNN7EXAMPLE used", "AKIAIOSFODNN7EXAMPLE"),
        ],
    )
    def test_credentials_redacted(self, raw, forbidden) -> None:
        from soar_lab.config.logging import SecretRedactorFilter

        record = logging.LogRecord("t", logging.INFO, __file__, 1, raw, (), None)
        SecretRedactorFilter().filter(record)
        assert forbidden not in record.getMessage()
        assert "REDACTED" in record.getMessage()

    def test_normal_message_untouched(self) -> None:
        from soar_lab.config.logging import SecretRedactorFilter

        record = logging.LogRecord("t", logging.INFO, __file__, 1, "worker processed 5", (), None)
        SecretRedactorFilter().filter(record)
        assert record.getMessage() == "worker processed 5"

    def test_percent_placeholder_after_sensitive_word_not_eaten(self) -> None:
        """BUG: 'password: %s' must keep the %s placeholder — redacting it
        orphans record.args and getMessage() raises TypeError."""
        from soar_lab.config.logging import SecretRedactorFilter

        record = logging.LogRecord(
            "t",
            logging.DEBUG,
            __file__,
            1,
            "Could not load Shuffle password: %s",
            (RuntimeError("boom"),),
            None,
        )
        SecretRedactorFilter().filter(record)
        assert record.getMessage() == "Could not load Shuffle password: boom"
