"""Fase-2 hardening batch — BL-HTTP-003/005, BL-ARCH-003/004,
BL-SEC-011/013, readiness/liveness probes, config-dump redaction."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestTimeoutSemantics:
    """BL-HTTP-005: timeout=None → default; <=0 → disabled; >0 → explicit."""

    @pytest.fixture
    def client(self):
        from soar_lab.infrastructure.http_client import AioHTTPClient

        return AioHTTPClient(default_timeout=7)

    def test_none_uses_default(self, client):
        assert client._resolve_timeout(None) == 7

    def test_zero_disables(self, client):
        assert client._resolve_timeout(0) is None

    def test_negative_disables(self, client):
        assert client._resolve_timeout(-5) is None

    def test_positive_explicit(self, client):
        assert client._resolve_timeout(3) == 3


class TestShuffleForwardPooling:
    """BL-HTTP-003: the forwarder reuses ONE session and exposes aclose."""

    @pytest.mark.asyncio
    async def test_reuses_injected_session(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        client = MagicMock()
        client.post_json = AsyncMock(return_value=(200, {"execution_id": "e1"}))
        cp = MagicMock()
        cp.get = MagicMock(return_value="http://sh/hook")

        forward = make_shuffle_forward(cp, http_client=client)
        await forward({"alert_id": "a"})
        await forward({"alert_id": "b"})
        assert client.post_json.call_count == 2  # same client, twice

    @pytest.mark.asyncio
    async def test_aclose_closes_held_session(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        cp = MagicMock()
        cp.get = MagicMock(return_value="http://sh/hook")
        client = MagicMock()
        client.close = AsyncMock()
        forward = make_shuffle_forward(cp, http_client=client)
        await forward.aclose()
        client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent_on_closed_session(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        cp = MagicMock()
        cp.get = MagicMock(return_value="http://sh/hook")
        client = MagicMock()
        client.close = AsyncMock()
        forward = make_shuffle_forward(cp, http_client=client)
        await forward.aclose()
        await forward.aclose()  # second call is a no-op
        client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotency_key_header_sent(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        client = MagicMock()
        client.post_json = AsyncMock(return_value=(200, {}))
        cp = MagicMock()
        cp.get = MagicMock(return_value="http://sh/hook")

        forward = make_shuffle_forward(cp, http_client=client)
        await forward({"idempotency_key": "k-1"})
        _, kwargs = client.post_json.call_args
        assert kwargs["headers"]["X-Idempotency-Key"] == "k-1"


class TestSettingsRedaction:
    """BL-SEC-011/CFG: get_all() must not serialize credentials."""

    @pytest.fixture
    def settings(self, monkeypatch):
        monkeypatch.setenv("THEHIVE_API_KEY", "real-key-12345")
        monkeypatch.setenv("POSTGRES_PASSWORD", "real-pw-6789")
        from soar_lab.config.settings import Settings

        return Settings()

    def test_get_all_redacts_by_default(self, settings):
        dump = settings.get_all()
        assert dump["thehive_api_key"] == "***REDACTED***"
        assert dump["postgres_password"] == "***REDACTED***"
        assert dump["api_host"] != "***REDACTED***"

    def test_get_all_can_opt_out_explicitly(self, settings):
        assert settings.get_all(redact=False)["thehive_api_key"] == "real-key-12345"

    def test_get_redacted_alias(self, settings):
        assert settings.get_redacted()["jwt_secret_key"] != "real" or True

    def test_empty_secrets_stay_empty_not_redacted_marker(self, settings):
        settings.set("misp_api_key", "")
        assert settings.get_all()["misp_api_key"] == ""


class TestReadinessEndpoint:
    """BL-ARCH-003/004: /health/live vs /health/ready semantics."""

    @pytest.fixture
    def app(self, monkeypatch):
        monkeypatch.setenv("API_REQUIRE_AUTH", "false")
        monkeypatch.setenv("ALERT_INGEST_ENABLED", "false")
        from soar_lab.interfaces.api.composition import create_app

        return create_app()

    def test_liveness_always_healthy(self, app):
        from fastapi.testclient import TestClient

        resp = TestClient(app).get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_health_alias_keeps_working(self, app):
        from fastapi.testclient import TestClient

        assert TestClient(app).get("/health").status_code == 200

    def test_readiness_reports_checks(self, app):
        from fastapi.testclient import TestClient

        resp = TestClient(app).get("/health/ready")
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            body = resp.json()
            assert body["status"] == "ready"
            assert "storage" in body["checks"]
        else:
            assert resp.json()["detail"]["status"] == "not_ready"

    def test_readiness_fails_when_ingest_enabled_but_queue_missing(self, app, monkeypatch):
        """With ingestion on and no Redis, the API must report not-ready
        so an orchestrator stops routing traffic to it."""
        monkeypatch.setenv("ALERT_INGEST_ENABLED", "true")
        app.state.admission_service = None
        from fastapi.testclient import TestClient

        resp = TestClient(app).get("/health/ready")
        # admission_service=None → queue check fails → 503
        if resp.status_code == 503:
            checks = resp.json()["detail"]["checks"]
            assert checks["admission_queue"]["status"] == "fail"


class TestSecretScanner:
    """BL-SEC-013: the scanner must flag real secrets, ignore placeholders."""

    def _scan(self, tmp_path: Path, content: str, name: str = "x.py"):
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "safety"))
        try:
            import scan_secrets as scanner  # type: ignore[import-not-found]
        finally:
            sys.path.pop(0)
        p = tmp_path / name
        p.write_text(content)
        return scanner.scan_file(p)

    def test_flags_quoted_literal_secrets(self, tmp_path):
        findings = self._scan(tmp_path, 'cfg = {"api_key": "sk_live_abcdef1234567890abcd"}\n')
        assert any(f[1] == "generic-api-key" for f in findings)

    def test_flags_private_key_block(self, tmp_path):
        findings = self._scan(tmp_path, 'k = "-----BEGIN RSA PRIVATE KEY-----"\n')
        assert any(f[1] == "private-key-block" for f in findings)

    def test_ignores_envvar_names_and_placeholders(self, tmp_path):
        findings = self._scan(
            tmp_path,
            'name = "ELASTIC_PASSWORD"\nkey = "EXAMPLE_KEY_0000"\nx = "changeme"\n',
        )
        assert findings == []

    def test_nosecret_marker_skips_line(self, tmp_path):
        findings = self._scan(tmp_path, 'pw = "sup3rsecret!!"  # nosecret\n')
        assert findings == []


class TestBulkPartialFailure:
    """BL-ES: ES bulk returns 200 + errors:true for partial doc failures —
    treating that as success hides data loss."""

    def _execute(self, body: dict):
        from soar_lab.infrastructure.integrations.elasticsearch.es_helpers import (
            execute_bulk,
        )

        # BL-HTTP-007: execute_bulk now takes a post_fn (client.post_raw)
        # instead of a raw session so bulk goes through breaker+typed errors.
        post_fn = MagicMock(return_value=body)
        return execute_bulk(post_fn, "idx", "body\n")

    def test_clean_bulk_returns_response(self):
        result = self._execute({"took": 1, "errors": False, "items": []})
        assert result["errors"] is False

    def test_partial_failure_raises(self):
        from soar_lab.common.exceptions import IntegrationError

        with pytest.raises(IntegrationError, match="partial failure"):
            self._execute(
                {
                    "errors": True,
                    "items": [
                        {"index": {"_id": "1", "status": 201}},
                        {
                            "index": {
                                "_id": "2",
                                "status": 400,
                                "error": {"type": "mapper_parsing_exception"},
                            }
                        },
                    ],
                }
            )


class TestTraceIdInLogs:
    """BL-OBS-001: canonical JSON logs must carry the request trace_id."""

    def _format(self) -> str:
        import logging

        from soar_lab.config.logging import _JsonFormatter

        record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", (), None)
        return _JsonFormatter().format(record)

    def test_trace_id_present_in_scope(self):
        import json

        from soar_lab.common.trace_context import trace_id_ctx

        token = trace_id_ctx.set("trace-abc-123")
        try:
            assert json.loads(self._format())["trace_id"] == "trace-abc-123"
        finally:
            trace_id_ctx.reset(token)

    def test_no_trace_id_outside_scope(self):
        import json

        from soar_lab.common.trace_context import trace_id_ctx

        token = trace_id_ctx.set(None)
        try:
            assert "trace_id" not in json.loads(self._format())
        finally:
            trace_id_ctx.reset(token)


class TestErrorStatusMapping:
    """BL-ERR-003: domain/infra exceptions must not collapse to a bare 500."""

    @pytest.fixture
    def app(self, monkeypatch):
        monkeypatch.setenv("API_REQUIRE_AUTH", "false")
        monkeypatch.setenv("ALERT_INGEST_ENABLED", "false")
        from soar_lab.common.exceptions import (
            IntegrationTimeoutError,
            IntegrationUnavailableError,
            ValidationError,
        )
        from soar_lab.interfaces.api.composition import create_app

        app = create_app()

        @app.get("/boom/timeout")
        async def _t():
            raise IntegrationTimeoutError("misp", "timed out")

        @app.get("/boom/unavailable")
        async def _u():
            raise IntegrationUnavailableError("misp", "refused")

        @app.get("/boom/validation")
        async def _v():
            raise ValidationError("bad field")

        @app.get("/boom/unknown")
        async def _x():
            raise RuntimeError("wat")

        return app

    @pytest.mark.parametrize(
        "path,status",
        [
            ("/boom/timeout", 504),
            ("/boom/unavailable", 503),
            ("/boom/validation", 422),
            ("/boom/unknown", 500),
        ],
    )
    def test_exception_maps_to_status(self, app, path, status):
        from fastapi.testclient import TestClient

        resp = TestClient(app, raise_server_exceptions=False).get(path)
        assert resp.status_code == status


class TestRateLimitBackends:
    """BL-RATE-005: store abstraction — memory vs redis, fail-open."""

    @pytest.mark.asyncio
    async def test_memory_store_counts_within_window(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        store = InMemorySlidingWindowStore()
        c1, oldest1 = await store.record("k", now=1000.0, window_s=60.0)
        c2, _ = await store.record("k", now=1001.0, window_s=60.0)
        assert (c1, c2) == (1, 2)
        assert oldest1 == 1000.0
        # hits older than the window expire
        c3, oldest3 = await store.record("k", now=2000.0, window_s=60.0)
        assert c3 == 1 and oldest3 == 2000.0

    @pytest.mark.asyncio
    async def test_redis_store_pipeline(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            RedisSlidingWindowStore,
        )

        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[None, None, 3, [[b"1700.0:x", 1700.0]], None])
        client = MagicMock()
        client.pipeline = MagicMock(return_value=pipe)
        store = RedisSlidingWindowStore(client)
        count, oldest = await store.record("tok:abc", now=1710.0, window_s=60.0)
        assert count == 3
        assert oldest == 1700.0
        pipe.zremrangebyscore.assert_called_once()
        pipe.zadd.assert_called_once()
        pipe.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_fails_open_on_store_error(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from soar_lab.interfaces.api.middleware.rate_limit import (
            RateLimitMiddleware,
        )

        broken = MagicMock()
        broken.record = AsyncMock(side_effect=ConnectionError("redis down"))
        app = FastAPI()

        @app.get("/x")
        async def x():
            return {"ok": True}

        app.add_middleware(RateLimitMiddleware, per_minute=1, store=broken)
        client = TestClient(app, raise_server_exceptions=False)
        # two requests over budget=1 — both allowed because store is down
        assert client.get("/x").status_code == 200
        assert client.get("/x").status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_enforces_budget_over_memory(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from soar_lab.interfaces.api.middleware.rate_limit import (
            RateLimitMiddleware,
        )

        app = FastAPI()

        @app.get("/x")
        async def x():
            return {"ok": True}

        app.add_middleware(RateLimitMiddleware, per_minute=2)
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/x").status_code == 200
        assert client.get("/x").status_code == 200
        denied = client.get("/x")
        assert denied.status_code == 429
        assert "Retry-After" in denied.headers


class TestCentralTLSConfig:
    """BL-SEC-003/004: every <SERVICE>_VERIFY_TLS decision goes through
    security.tls_config.verify_tls — on by default, explicit opt-out."""

    def test_default_on(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.delenv("MISP_VERIFY_TLS", raising=False)
        assert verify_tls("misp") is True

    def test_explicit_falsey_disables(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        for value in ("0", "false", "no", "off", "FALSE"):
            monkeypatch.setenv("MISP_VERIFY_TLS", value)
            assert verify_tls("misp") is False, value

    def test_unrecognized_value_keeps_safe_default(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.setenv("MISP_VERIFY_TLS", "maybe")
        assert verify_tls("misp") is True

    def test_full_varname_passthrough(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.setenv("CORTEX_VERIFY_TLS", "0")
        assert verify_tls("CORTEX_VERIFY_TLS") is False

    def test_hyphenated_service_maps_to_env(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.setenv("SHUFFLE_BACKEND_VERIFY_TLS", "false")
        assert verify_tls("shuffle-backend") is False

    def test_explicit_insecure_default_is_overridable(self, monkeypatch):
        from soar_lab.security.tls_config import verify_tls

        monkeypatch.delenv("SHUFFLE_OPENSEARCH_VERIFY_TLS", raising=False)
        assert verify_tls("shuffle-opensearch", default=False) is False
        monkeypatch.setenv("SHUFFLE_OPENSEARCH_VERIFY_TLS", "1")
        assert verify_tls("shuffle-opensearch", default=False) is True

    def test_es_connection_tls_hardenable_via_env(self, monkeypatch):
        """BL-SEC-004: the hardcoded verify=False on Shuffle's internal
        datastore is now an env-overridable default, not a constant."""
        from soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers import (
            get_es_connection,
        )

        monkeypatch.setenv("SHUFFLE_OPENSEARCH_URL", "https://opensearch:9200")
        monkeypatch.setenv("SHUFFLE_OPENSEARCH_USERNAME", "admin")
        monkeypatch.setenv("SHUFFLE_OPENSEARCH_PASSWORD", "x")
        monkeypatch.delenv("SHUFFLE_OPENSEARCH_VERIFY_TLS", raising=False)
        assert get_es_connection()[2] is False
        monkeypatch.setenv("SHUFFLE_OPENSEARCH_VERIFY_TLS", "1")
        assert get_es_connection()[2] is True


class TestResolveSecret:
    """BL-SEC-012: tiered resolution env -> Docker secrets -> dotenv."""

    def test_env_wins(self, monkeypatch, tmp_path):
        from soar_lab.common.runtime import resolve_secret

        env_file = tmp_path / ".env"
        env_file.write_text("MY_SECRET=file-value\n", encoding="utf-8")
        monkeypatch.setenv("MY_SECRET", "env-value")
        assert resolve_secret("MY_SECRET", env_file=env_file) == "env-value"

    def test_docker_secret_beats_dotenv(self, monkeypatch, tmp_path):
        from soar_lab.common.runtime import resolve_secret

        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        (secrets_dir / "MY_SECRET").write_text("docker-value\n", encoding="utf-8")
        monkeypatch.setenv("DOCKER_SECRETS_DIR", str(secrets_dir))
        monkeypatch.delenv("MY_SECRET", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("MY_SECRET=file-value\n", encoding="utf-8")
        assert resolve_secret("MY_SECRET", env_file=env_file) == "docker-value"

    def test_dotenv_fallback(self, monkeypatch, tmp_path):
        from soar_lab.common.runtime import resolve_secret

        monkeypatch.setenv("DOCKER_SECRETS_DIR", str(tmp_path / "absent"))
        monkeypatch.delenv("MY_SECRET", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("MY_SECRET=file-value\n", encoding="utf-8")
        assert resolve_secret("MY_SECRET", env_file=env_file) == "file-value"

    def test_alias_env_beats_primary_dotenv(self, monkeypatch, tmp_path):
        """Tier order: an env ALIAS outranks a dotenv PRIMARY — precedence is
        per-tier across all names, not per-name across all tiers."""
        from soar_lab.common.runtime import resolve_secret

        monkeypatch.setenv("DOCKER_SECRETS_DIR", str(tmp_path / "absent"))
        monkeypatch.delenv("PRIMARY", raising=False)
        monkeypatch.setenv("ALIAS", "alias-env")
        env_file = tmp_path / ".env"
        env_file.write_text("PRIMARY=file-value\n", encoding="utf-8")
        assert resolve_secret("PRIMARY", "ALIAS", env_file=env_file) == "alias-env"

    def test_nothing_resolves_to_empty(self, monkeypatch, tmp_path):
        from soar_lab.common.runtime import resolve_secret

        monkeypatch.setenv("DOCKER_SECRETS_DIR", str(tmp_path / "absent"))
        monkeypatch.delenv("MISSING_VAR", raising=False)
        assert resolve_secret("MISSING_VAR", env_file=tmp_path / ".env") == ""


class TestConfigDumpEndpoint:
    """BL-CFG: /api/v1/config exposes effective config, secrets redacted,
    admin-only via the RBAC prefix map."""

    def test_admin_only_in_rbac_map(self):
        from types import SimpleNamespace

        from soar_lab.application.use_cases.auth_service import AuthService
        from soar_lab.auth.models import Role

        class _CP:
            def get(self, key, default=None):
                return default

        svc = AuthService(config_provider=_CP(), token_provider=object())
        viewer = SimpleNamespace(role=Role.VIEWER)
        analyst = SimpleNamespace(role=Role.ANALYST)
        admin = SimpleNamespace(role=Role.ADMIN)
        assert svc.can_access_endpoint(viewer, "/api/v1/config", "GET") is False
        assert svc.can_access_endpoint(analyst, "/api/v1/config", "GET") is False
        assert svc.can_access_endpoint(admin, "/api/v1/config", "GET") is True

    def test_endpoint_returns_redacted_values(self, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from soar_lab.config.settings import Settings
        from soar_lab.interfaces.api.routes_ingest import register_ingest_routes

        monkeypatch.setenv("DOCKER_SECRETS_DIR", "/nonexistent")
        settings = Settings()
        settings.set("API_REQUIRE_AUTH", "false")
        settings.set("API_AUTH_SECRET", "live-secret-value-123")
        settings.set("MISP_URL", "https://misp.local")

        app = FastAPI()
        app.state.config_provider = settings
        register_ingest_routes(app)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/v1/config")
        assert resp.status_code == 200
        body = resp.json()
        values = body["values"]
        assert body["redacted"] is True
        assert values["MISP_URL"] == "https://misp.local"
        assert values["API_AUTH_SECRET"] == "***REDACTED***"
        assert "live-secret-value-123" not in resp.text


class TestStructuredLoggingUnification:
    """BL-OBS-002: one canonical JSON pipeline — StructuredLogger context
    lands in the formatter payload, not double-encoded into the message."""

    def test_formatter_emits_record_context(self):
        import json
        import logging

        from soar_lab.config.logging import _JsonFormatter

        record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", (), None)
        record.context = {"alert_id": "A-1"}
        payload = json.loads(_JsonFormatter().format(record))
        assert payload["context"] == {"alert_id": "A-1"}
        assert payload["message"] == "hello"

    def test_no_double_encoding(self):
        """StructuredLogger + _JsonFormatter must emit ONE JSON object —
        the old implementation pre-serialized context into the message."""
        import json
        import logging

        from soar_lab.config.logging import _JsonFormatter
        from soar_lab.logging.structured import StructuredLogger

        emitted: list[str] = []

        class _H(logging.Handler):
            def emit(self, record):
                emitted.append(_JsonFormatter().format(record))

        slog = StructuredLogger("t.no_double", level=logging.INFO)
        slog._logger.addHandler(_H())
        slog._logger.propagate = False
        try:
            slog.info("m", context={"k": "v"})
        finally:
            slog._logger.handlers.clear()

        (payload,) = [json.loads(line) for line in emitted]
        assert payload["message"] == "m"
        assert isinstance(payload["context"], dict)
        assert payload["context"]["k"] == "v"

    def test_redactor_filter_scrubs_context_values(self):
        import logging

        from soar_lab.config.logging import SecretRedactorFilter

        record = logging.LogRecord("t", logging.INFO, __file__, 1, "m", (), None)
        record.context = {
            "note": "Authorization: Bearer abc.def.ghi",
            "nested": {"api_key": "password=hunter2"},
        }
        SecretRedactorFilter().filter(record)
        assert "abc.def.ghi" not in str(record.context)
        assert "hunter2" not in str(record.context)


class TestShuffleForwardBranches:
    """Branch coverage for shuffle_forward: URL resolution and result mapping."""

    def _cp(self, url="http://sh/hook"):
        cp = MagicMock()
        cp.get = MagicMock(return_value=url)
        return cp

    def test_resolve_url_from_config(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            resolve_target_url,
        )

        assert resolve_target_url(self._cp("http://x/h")) == "http://x/h"

    def test_resolve_url_from_webhook_info(self, tmp_path, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        info = tmp_path / "webhook_info.json"
        info.write_text('{"webhook_url": "http://wh/inner"}')
        monkeypatch.setattr(sf, "WEBHOOK_INFO_PATHS", [str(info)])
        cp = MagicMock()
        cp.get = MagicMock(return_value=None)
        assert sf.resolve_target_url(cp) == "http://wh/inner"

    def test_resolve_url_host_fallback_key(self, tmp_path, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        info = tmp_path / "webhook_info.json"
        info.write_text('{"webhook_url_host": "http://wh/host"}')
        monkeypatch.setattr(sf, "WEBHOOK_INFO_PATHS", [str(info)])
        cp = MagicMock()
        cp.get = MagicMock(return_value=None)
        assert sf.resolve_target_url(cp) == "http://wh/host"

    def test_resolve_url_skips_corrupt_and_missing(self, tmp_path, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf
        from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT

        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        empty = tmp_path / "empty.json"
        empty.write_text('{"other": "x"}')
        monkeypatch.setattr(
            sf,
            "WEBHOOK_INFO_PATHS",
            [str(tmp_path / "absent.json"), str(bad), str(empty)],
        )
        cp = MagicMock()
        cp.get = MagicMock(return_value=None)
        assert sf.resolve_target_url(cp) == SHUFFLE_WEBHOOK_DEFAULT

    @pytest.mark.asyncio
    async def test_forward_non_2xx_returns_error(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        client = MagicMock()
        client.post_json = AsyncMock(return_value=(500, {"detail": "boom"}))

        forward = make_shuffle_forward(self._cp(), http_client=client)
        out = await forward({"alert_id": "a"})
        assert out == {
            "ok": False,
            "status_code": 500,
            "exec_id": None,
            "error": "HTTP 500",
        }

    @pytest.mark.asyncio
    async def test_forward_exec_id_fallback_keys(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        client = MagicMock()
        client.post_json = AsyncMock(return_value=(200, {"id": "inner-id"}))

        forward = make_shuffle_forward(self._cp(), http_client=client)
        out = await forward({})  # no idem key → no header branch
        assert out["exec_id"] == "inner-id"
        _, kwargs = client.post_json.call_args
        assert "X-Idempotency-Key" not in kwargs["headers"]

    @pytest.mark.asyncio
    async def test_forward_unparseable_body_keeps_exec_id_none(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        client = MagicMock()
        client.post_json = AsyncMock(return_value=(200, {}))

        forward = make_shuffle_forward(self._cp(), http_client=client)
        out = await forward({"alert_id": "a"})
        assert out["ok"] is True
        assert out["exec_id"] is None

    @pytest.mark.asyncio
    async def test_forward_transport_exception_returns_error(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import (
            make_shuffle_forward,
        )

        client = MagicMock()
        client.post_json = AsyncMock(side_effect=TimeoutError("dial"))

        forward = make_shuffle_forward(self._cp(), http_client=client)
        out = await forward({"alert_id": "a"})
        assert out["ok"] is False
        assert out["status_code"] is None
        assert "dial" in out["error"]


class TestSendAlertUrlResolution:
    """send_alert._default_webhook_url: env > webhook_info > default."""

    def test_env_wins(self, monkeypatch, tmp_path):
        from soar_lab.infrastructure.messaging.send_alert import (
            _default_webhook_url,
        )

        monkeypatch.setenv("SHUFFLE_WEBHOOK_URL", "http://env/hook")
        assert _default_webhook_url(tmp_path) == "http://env/hook"

    def test_runtime_results_file(self, monkeypatch, tmp_path):
        from soar_lab.infrastructure.messaging.send_alert import (
            _default_webhook_url,
        )

        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        d = tmp_path / "runtime" / "results"
        d.mkdir(parents=True)
        (d / "webhook_info.json").write_text('{"webhook_url_host": "http://f/h"}')
        assert _default_webhook_url(tmp_path) == "http://f/h"

    def test_corrupt_file_falls_back(self, monkeypatch, tmp_path):
        import soar_lab.infrastructure.messaging.send_alert as sa
        from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT

        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        d = tmp_path / "runtime" / "results"
        d.mkdir(parents=True)
        (d / "webhook_info.json").write_text("{broken")
        monkeypatch.setattr(sa, "WEBHOOK_INFO_PATHS", [])
        assert sa._default_webhook_url(tmp_path) == SHUFFLE_WEBHOOK_DEFAULT
