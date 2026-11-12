#!/usr/bin/env python3
"""Coverage for shuffle_forward: egress validation, retry classification,
signed envelope forwarding."""

import pytest
import requests

from soar_lab.infrastructure.messaging.shuffle_forward import (
    DestinationPolicyError,
    _classify,
    _validate_target,
    make_shuffle_forward,
)


class TestValidateTarget:
    def test_malformed_url(self):
        with pytest.raises(DestinationPolicyError, match="malformed"):
            _validate_target("http://[bad", None)

    def test_scheme_not_allowed(self):
        with pytest.raises(DestinationPolicyError, match="scheme"):
            _validate_target("ftp://h/x", None)

    def test_credentials_forbidden(self):
        with pytest.raises(DestinationPolicyError, match="credentials"):
            _validate_target("http://u:p@h/x", None)

    def test_host_not_in_allowlist(self):
        with pytest.raises(DestinationPolicyError, match="allowlist"):
            _validate_target("http://evil/x", {"shuffle-backend"})

    def test_allowed(self):
        assert _validate_target("http://ok/x", {"ok"}) == "http://ok/x"


class TestClassify:
    def test_timeout(self):
        r = _classify(None, requests.Timeout())
        assert r == {"error_code": "DOWNSTREAM_TIMEOUT", "retryable": True}

    def test_conn_error(self):
        r = _classify(None, requests.ConnectionError())
        assert r == {"error_code": "DOWNSTREAM_UNAVAILABLE", "retryable": True}

    def test_other_exc(self):
        assert _classify(None, RuntimeError())["error_code"] == "FORWARD_ERROR"

    def test_none_status(self):
        assert _classify(None, None)["error_code"] == "FORWARD_ERROR"

    def test_429(self):
        assert _classify(429, None)["error_code"] == "DOWNSTREAM_RATE_LIMITED"

    def test_5xx(self):
        assert _classify(503, None)["error_code"] == "DOWNSTREAM_5XX"

    def test_rejected(self):
        assert _classify(422, None) == {
            "error_code": "DOWNSTREAM_REJECTED",
            "retryable": False,
        }

    def test_2xx_ok(self):
        assert _classify(200, None) == {"error_code": None, "retryable": False}

    def test_other_status(self):
        assert _classify(301, None)["error_code"] == "DOWNSTREAM_HTTP_301"


class _Cfg:
    def __init__(self, kv):
        self.kv = kv

    def get(self, k):
        return self.kv.get(k)


class TestResolveTargetUrl:
    def test_env_url_wins(self):
        from soar_lab.infrastructure.messaging.shuffle_forward import resolve_target_url

        cfg = _Cfg({"SHUFFLE_WEBHOOK_URL": "http://env/hook"})
        assert resolve_target_url(cfg) == "http://env/hook"

    def test_webhook_info_file(self, tmp_path, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        info = tmp_path / "webhook_info.json"
        info.write_text('{"webhook_url": "http://file/hook"}', encoding="utf-8")
        monkeypatch.setattr(sf, "WEBHOOK_INFO_PATHS", [str(tmp_path / "nope"), str(info)])
        assert sf.resolve_target_url(_Cfg({})) == "http://file/hook"

    def test_bad_json_falls_through_to_default(self, tmp_path, monkeypatch, caplog):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        bad = tmp_path / "webhook_info.json"
        bad.write_text("{invalid", encoding="utf-8")
        monkeypatch.setattr(sf, "WEBHOOK_INFO_PATHS", [str(bad)])
        assert sf.resolve_target_url(_Cfg({})) == sf.SHUFFLE_WEBHOOK_DEFAULT

    def test_missing_file_warns_and_defaults(self, monkeypatch, caplog):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        monkeypatch.setattr(sf, "WEBHOOK_INFO_PATHS", ["/nonexistent/x.json"])
        with caplog.at_level("WARNING"):
            url = sf.resolve_target_url(_Cfg({}))
        assert url == sf.SHUFFLE_WEBHOOK_DEFAULT
        assert "falling back" in caplog.text


class TestForwardClientLifecycle:
    async def test_owned_client_created_closed_and_reopened(self, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        created = []

        class FakeClient:
            def __init__(self, default_timeout):
                self.closed = False
                created.append(self)

            async def post_json(self, target, payload, timeout):
                return 200, {"execution_id": "e1"}

            async def close(self):
                self.closed = True

        monkeypatch.setattr(sf, "AioHTTPClient", FakeClient)
        fwd = sf.make_shuffle_forward(
            _Cfg({"ALERT_INGEST_TARGET_URL": "http://x"}), http_client=None
        )
        res = await fwd({"alert_id": "a"})
        assert res["ok"] is True and res["exec_id"] == "e1"
        assert len(created) == 1
        await fwd.aclose()
        assert created[0].closed is True
        await fwd.aclose()  # idempotent
        res = await fwd({"alert_id": "b"})
        assert res["ok"] is True
        assert len(created) == 2  # reopened after close

    async def test_post_exception_returns_structured_error(self):
        class BadClient:
            async def post_json(self, target, payload, timeout):
                raise requests.Timeout("boom")

        fwd = make_shuffle_forward(
            _Cfg({"ALERT_INGEST_TARGET_URL": "http://x"}), http_client=BadClient()
        )
        res = await fwd({"alert_id": "a"})
        assert res["ok"] is False
        assert res["status_code"] is None
        assert res["error_code"] == "DOWNSTREAM_TIMEOUT"
        assert res["retryable"] is True

    async def test_forward_unsigned_no_security_block(self):
        sent = {}

        class Client:
            async def post_json(self, target, payload, timeout):
                sent.update(payload)
                return 200, {}

        fwd = make_shuffle_forward(
            _Cfg({"ALERT_INGEST_TARGET_URL": "http://x"}), http_client=Client()
        )
        res = await fwd({"alert_id": "a"})
        assert res["ok"] is True
        assert "security" not in sent
        assert sent["schema_version"] == "1.0"


class TestForwardSigning:
    async def test_signing_key_produces_security_block(self):
        sent = {}

        class Client:
            async def post_json(self, target, payload, timeout):
                sent.update(payload)
                return 200, {"ok": True}

        cfg = _Cfg(
            {
                "ALERT_INGEST_TARGET_URL": "http://shuffle/hook",
                "ALERT_SIGNING_KEY": "k" * 40,
                "ALERT_SIGNING_KEY_ID": "kid-1",
            }
        )
        fwd = make_shuffle_forward(cfg, http_client=Client())
        res = await fwd({"alert_id": "a1"})
        assert res["ok"] is True
        assert "security" in sent  # signed envelope
