#!/usr/bin/env python3
"""Mutation-hardening tests for shuffle_forward + redis_admission_store —
egress policy, classify table, envelope contract, Redis key semantics."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import requests

from soar_lab.infrastructure.messaging.redis_admission_store import (
    RedisAdmissionStore,
)
from soar_lab.infrastructure.messaging.shuffle_forward import (
    DestinationPolicyError,
    _classify,
    _validate_target,
    make_shuffle_forward,
    resolve_target_url,
)


class TestValidateTarget:
    def test_scheme_allowlist(self):
        with pytest.raises(DestinationPolicyError, match="scheme 'ftp' not allowed"):
            _validate_target("ftp://x/y", None)
        with pytest.raises(DestinationPolicyError, match="scheme ''"):
            _validate_target("no-scheme", None)

    def test_credentials_forbidden(self):
        with pytest.raises(DestinationPolicyError, match="credentials in forward URL"):
            _validate_target("http://u:p@h/", None)

    def test_host_allowlist(self):
        assert _validate_target("http://ok/x", {"ok"}) == "http://ok/x"
        with pytest.raises(DestinationPolicyError, match="host 'bad' not in"):
            _validate_target("http://bad/x", {"ok"})
        # empty allowlist = permissive lab default
        assert _validate_target("http://any/x", None) == "http://any/x"

    def test_malformed_url(self):
        with pytest.raises(DestinationPolicyError, match="malformed forward URL"):
            _validate_target("http://[::1", None)


class TestResolveTargetUrl:
    def _cfg(self, d):
        return MagicMock(get=lambda k, _d=d: _d.get(k))

    def test_env_priority(self):
        cfg = self._cfg(
            {
                "ALERT_INGEST_TARGET_URL": "http://a/",
                "SHUFFLE_WEBHOOK_URL": "http://b/",
            }
        )
        assert resolve_target_url(cfg) == "http://a/"
        cfg2 = self._cfg({"SHUFFLE_WEBHOOK_URL": "http://b/"})
        assert resolve_target_url(cfg2) == "http://b/"

    def test_webhook_info_fallback(self, tmp_path, monkeypatch):
        info = tmp_path / "webhook_info.json"
        info.write_text(json.dumps({"webhook_url": "http://w/"}))
        monkeypatch.setattr(
            "soar_lab.infrastructure.messaging.shuffle_forward.WEBHOOK_INFO_PATHS",
            [str(info)],
        )
        assert resolve_target_url(self._cfg({})) == "http://w/"

    def test_webhook_info_host_fallback(self, tmp_path, monkeypatch):
        info = tmp_path / "webhook_info.json"
        info.write_text(json.dumps({"webhook_url_host": "http://wh/"}))
        monkeypatch.setattr(
            "soar_lab.infrastructure.messaging.shuffle_forward.WEBHOOK_INFO_PATHS",
            [str(info)],
        )
        assert resolve_target_url(self._cfg({})) == "http://wh/"

    def test_default_and_warning(self, tmp_path, monkeypatch, caplog):
        import logging

        from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT

        monkeypatch.setattr(
            "soar_lab.infrastructure.messaging.shuffle_forward.WEBHOOK_INFO_PATHS",
            [str(tmp_path / "missing.json")],
        )
        with caplog.at_level(logging.WARNING):
            assert resolve_target_url(self._cfg({})) == SHUFFLE_WEBHOOK_DEFAULT
        assert "falling back to default webhook URL" in caplog.text


class TestClassify:
    def test_exception_table(self):
        assert _classify(None, requests.Timeout("t")) == {
            "error_code": "DOWNSTREAM_TIMEOUT",
            "retryable": True,
        }
        assert _classify(None, requests.ConnectionError("c")) == {
            "error_code": "DOWNSTREAM_UNAVAILABLE",
            "retryable": True,
        }
        assert _classify(None, ValueError("x")) == {
            "error_code": "FORWARD_ERROR",
            "retryable": True,
        }
        assert _classify(None, None) == {
            "error_code": "FORWARD_ERROR",
            "retryable": True,
        }

    @pytest.mark.parametrize(
        "status,code,retry",
        [
            (429, "DOWNSTREAM_RATE_LIMITED", True),
            (500, "DOWNSTREAM_5XX", True),
            (503, "DOWNSTREAM_5XX", True),
            (400, "DOWNSTREAM_REJECTED", False),
            (401, "DOWNSTREAM_REJECTED", False),
            (403, "DOWNSTREAM_REJECTED", False),
            (404, "DOWNSTREAM_REJECTED", False),
            (422, "DOWNSTREAM_REJECTED", False),
            (200, None, False),
            (299, None, False),
            (302, "DOWNSTREAM_HTTP_302", False),
            (418, "DOWNSTREAM_HTTP_418", False),
        ],
    )
    def test_status_table(self, status, code, retry):
        assert _classify(status, None) == {"error_code": code, "retryable": retry}


class TestForward:
    def _forward(self, post_result=(200, {"execution_id": "e1"}), **cfg):
        provider = MagicMock(
            get=lambda k, _d={
                "ALERT_INGEST_TARGET_URL": "http://shuffle/hook",
                **cfg,
            }: _d.get(k)
        )
        client = AsyncMock()
        client.post_json.return_value = post_result
        fwd = make_shuffle_forward(provider, http_client=client)
        return fwd, client

    async def test_envelope_contract(self):
        fwd, client = self._forward()
        out = await fwd({"alert_id": "a1", "delivery_id": "d1", "attempt": 2, "x": 1})
        (url,), kw = client.post_json.call_args
        assert url == "http://shuffle/hook"
        payload = kw["payload"]
        assert payload["schema_version"] == "1.0"
        assert payload["event_id"] == "a1"
        assert payload["delivery_id"] == "d1"
        assert payload["attempt"] == 2
        assert payload["idempotency_key"] == "a1"  # falls back to alert_id
        assert payload["x"] == 1
        assert out == {
            "ok": True,
            "status_code": 200,
            "exec_id": "e1",
            "error_code": None,
            "retryable": False,
        }

    async def test_envelope_defaults(self):
        fwd, client = self._forward()
        await fwd({})
        payload = client.post_json.call_args.kwargs["payload"]
        assert payload["event_id"].startswith("evt-")
        assert payload["delivery_id"].startswith("dlv-")
        assert payload["attempt"] == 1
        assert payload["idempotency_key"] is None

    async def test_exec_id_fallbacks(self):
        for resp, want in [
            ({"execution_id": "a"}, "a"),
            ({"executionId": "b"}, "b"),
            ({"id": "c"}, "c"),
            ({}, None),
        ]:
            fwd, client = self._forward(post_result=(200, resp))
            out = await fwd({})
            assert out["exec_id"] == want, resp

    async def test_exception_classified_and_logged(self, caplog):
        import logging

        fwd, client = self._forward()
        client.post_json.side_effect = requests.Timeout("t")
        with caplog.at_level(logging.WARNING):
            out = await fwd({})
        assert out == {
            "ok": False,
            "status_code": None,
            "exec_id": None,
            "error_code": "DOWNSTREAM_TIMEOUT",
            "retryable": True,
        }
        assert "forward to" in caplog.text

    async def test_signed_envelope(self):
        fwd, client = self._forward(
            ALERT_SIGNING_KEY="k" * 32, ALERT_SIGNING_KEY_ID="kid-1"
        )
        await fwd({"alert_id": "a"})
        payload = client.post_json.call_args.kwargs["payload"]
        assert "security" in payload
        assert payload["security"]["key_id"] == "kid-1"
        assert payload["security"]["alg"]
        assert payload["security"]["signature"]
        assert payload["security"]["payload_sha256"]

    async def test_unsigned_no_security(self):
        fwd, client = self._forward()
        await fwd({})
        assert "security" not in client.post_json.call_args.kwargs["payload"]

    async def test_client_lifecycle(self):
        provider = MagicMock(
            get=lambda k: {"ALERT_INGEST_TARGET_URL": "http://s/"}.get(k)
        )
        fwd = make_shuffle_forward(provider)
        with pytest.MonkeyPatch.context() as mp:
            made = []

            class FakeClient:
                def __init__(self, **kw):
                    made.append(kw)
                    self.post_json = AsyncMock(return_value=(200, {}))
                    self.close = AsyncMock()

            mp.setattr(
                "soar_lab.infrastructure.messaging.shuffle_forward.AioHTTPClient",
                FakeClient,
            )
            await fwd({})
            assert made == [{"default_timeout": 30}]
            await fwd.aclose()
            await fwd.aclose()  # idempotent
            await fwd({})  # owned+closed -> new client
            assert len(made) == 2

    async def test_injected_client_not_recreated(self):
        client = AsyncMock()
        client.post_json.return_value = (200, {})
        provider = MagicMock(
            get=lambda k: {"ALERT_INGEST_TARGET_URL": "http://s/"}.get(k)
        )
        fwd = make_shuffle_forward(provider, http_client=client)
        await fwd({})
        await fwd.aclose()
        client.close.assert_awaited_once()
        # injected client is reused even after close (not owned)
        await fwd({})
        assert client.post_json.await_count == 2


class TestRedisAdmissionStore:
    def _store(self):
        c = AsyncMock()
        return RedisAdmissionStore(c, record_ttl_s=100), c

    async def test_create_mapping_and_ttl(self):
        s, c = self._store()
        await s.create(
            {"admission_id": "a1", "nested": {"k": 1}, "lst": [1], "n": 5}
        )
        key, kw = c.hset.call_args.args[0], c.hset.call_args.kwargs
        assert key == "soar:admission:a1"
        m = kw["mapping"]
        assert m["nested"] == '{"k": 1}' and m["lst"] == "[1]" and m["n"] == "5"
        c.expire.assert_awaited_once_with("soar:admission:a1", 100)

    async def test_update_vanished_warns(self, caplog):
        import logging

        s, c = self._store()
        c.exists.return_value = 0
        with caplog.at_level(logging.WARNING):
            await s.update("a1", {"status": "x"})
        assert "vanished before update" in caplog.text
        c.hset.assert_not_awaited()

    async def test_update_serializes(self):
        s, c = self._store()
        c.exists.return_value = 1
        await s.update("a1", {"st": {"x": 1}, "n": 2})
        m = c.hset.call_args.kwargs["mapping"]
        assert m["st"] == '{"x": 1}' and m["n"] == "2"

    async def test_get_decode(self):
        s, c = self._store()
        c.hgetall.return_value = {}
        assert await s.get("a1") is None
        c.hgetall.return_value = {b"status": b'"q"', b"raw": b"plain", "n": "3"}
        out = await s.get("a1")
        assert out == {"status": "q", "raw": "plain", "n": 3}
        assert c.hgetall.call_args.args == ("soar:admission:a1",)

    async def test_find_by_key(self):
        s, c = self._store()
        c.get.return_value = None
        assert await s.find_by_key("k") is None
        c.get.return_value = b"a1"
        assert await s.find_by_key("k") == "a1"
        assert c.get.call_args.args == ("soar:admission:key:k",)

    async def test_bind_and_try_bind(self):
        s, c = self._store()
        await s.bind_key("k", "a1")
        c.set.assert_awaited_once_with(
            "soar:admission:key:k", "a1", ex=100, nx=True
        )
        c.set.return_value = True
        assert await s.try_bind_key("k", "a1") is None
        c.set.return_value = None
        c.get.return_value = b"winner"
        assert await s.try_bind_key("k", "a1") == "winner"
        c.get.return_value = None
        assert await s.try_bind_key("k", "a1") == "a1"  # lost & no record -> own id

    async def test_list_by_status_filters_and_limits(self):
        s, c = self._store()

        async def scan(match=""):
            for k in [b"soar:admission:1", b"soar:admission:key:x", b"soar:admission:2"]:
                yield k

        c.scan_iter = scan
        c.hgetall.side_effect = [
            {b"status": b'"dead"'},
            {b"status": b'"queued"'},
        ]
        out = await s.list_by_status({"dead", "queued"}, limit=10)
        assert len(out) == 2
        assert c.hgetall.await_count == 2  # key-prefix entries skipped
        c.hgetall.assert_awaited_with("soar:admission:2")

    async def test_list_by_status_limit_breaks(self):
        s, c = self._store()

        async def scan(match=""):
            for i in range(5):
                yield f"soar:admission:{i}".encode()

        c.scan_iter = scan
        c.hgetall.return_value = {b"status": b'"dead"'}
        out = await s.list_by_status({"dead"}, limit=2)
        assert len(out) == 2

    async def test_unbind_key_eval(self):
        s, c = self._store()
        await s.unbind_key("k", "a1")
        script, nkeys, key, arg = c.eval.call_args.args
        assert "GET" in script and "DEL" in script
        assert nkeys == 1
        assert key == "soar:admission:key:k" and arg == "a1"
