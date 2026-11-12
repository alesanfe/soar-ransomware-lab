#!/usr/bin/env python3
"""Mutation-hardening tests for redaction, sanitization, tls_config and
bulkhead — exact replacement strings, boundary values, error contracts."""

from __future__ import annotations

import asyncio
import base64
import json

import pytest

from soar_lab.resilience.bulkhead import (
    AsyncBulkhead,
    Bulkhead,
    BulkheadFullError,
)
from soar_lab.security.redaction import redact_text, redact_url, safe_error
from soar_lab.security.sanitization import PayloadSanitizer
from soar_lab.security.tls_config import ca_verify, verify_tls


class TestRedactText:
    def test_none_and_control_chars(self):
        assert redact_text(None) == ""
        assert redact_text("a\x00b\x1fc") == "a b c"

    def test_hook_path_redacted(self):
        out = redact_text("POST /api/v1/hooks/webhook_abc123-XYZ_ok done")
        assert out == "POST /api/v1/hooks/[redacted] done"

    def test_bearer_redacted(self):
        out = redact_text("auth: Bearer abcdefghijklmnop")
        assert out == "auth: Bearer [redacted]"

    def test_secret_kv_redacted(self):
        out = redact_text("token=abc123 secret: xyz")
        # separator (group 2) is preserved verbatim between key and mask
        assert out == "token=[redacted] secret: [redacted]"

    def test_hex_blob_redacted(self):
        out = redact_text("sig " + "a" * 64 + " end")
        assert out == "sig [redacted-hex] end"

    def test_query_string_redacted(self):
        out = redact_text("GET http://h/path?key=secret&x=1 done")
        assert "?[redacted]" in out and "key=secret" not in out

    def test_max_len_truncation(self):
        out = redact_text("x" * 300)
        assert len(out) == 201 and out.endswith("…")
        assert redact_text("x" * 200) == "x" * 200


class TestRedactUrl:
    def test_strips_path_and_query(self):
        assert redact_url("https://h:8443/api/v1/hooks/webhook_x?k=v") == (
            "https://h:8443"
        )

    def test_defaults(self):
        assert redact_url("http://host/") == "http://host"
        # no hostname parseable -> 'unknown' host with default scheme
        assert redact_url("no-scheme/path") == "http://unknown"


class TestSafeError:
    def test_contract(self):
        out = safe_error(
            RuntimeError("Bearer abcdefghijkl broke"), code="FWD_ERR", retryable=True
        )
        assert out["code"] == "FWD_ERR"
        assert out["destination"] == "downstream"
        assert out["retryable"] is True
        assert out["message"] == "Bearer [redacted] broke"

    def test_none_and_empty_fallback(self):
        out = safe_error(None, code="MY_CODE", retryable=False, destination="q")
        assert out == {
            "code": "MY_CODE",
            "destination": "q",
            "retryable": False,
            "message": "my_code",
        }

    def test_message_max_len_160(self):
        out = safe_error("x" * 300, code="C", retryable=True)
        assert len(out["message"]) == 161


class TestSanitizer:
    def test_dict_whitelist_blacklist(self):
        s = PayloadSanitizer()
        out = s.sanitize({"a": 1, "b": 2, "c": 3}, whitelist=["a", "b"], blacklist=["b"])
        assert out == {"a": 1}

    def test_recursive_and_list(self):
        s = PayloadSanitizer()
        out = s.sanitize({"x": ["<script>a</script>", {"y": "DROP TABLE t"}]})
        assert out == {"x": ["", {"y": " t"}]}

    def test_fixpoint_removal(self):
        s = PayloadSanitizer()
        # nested pattern that re-forms after one pass
        assert "<script" not in s.sanitize("<scr<script></script>ipt>alert</script>")
        assert s.sanitize("javascript:javascript:alert(1)") == "alert(1)"

    def test_control_and_null(self):
        s = PayloadSanitizer()
        assert s.sanitize("a\x00b\x07c\x7f") == "abc"

    def test_on_event_and_truncation(self):
        s = PayloadSanitizer()
        # on-attr regex eats `onerror="alert(1)` but leaves the closing `">`
        assert s.sanitize('<img src=x onerror="alert(1)">') == '<img src=x">'
        assert len(s.sanitize("z" * 60000)) == 1000  # DEFAULT_SANITIZATION_MAX_LENGTH

    def test_sanitize_html_and_js(self):
        s = PayloadSanitizer()
        assert s.sanitize_html("<script>x</script><b onclick=y>t</b>") == "<b>t</b>"
        assert s.sanitize_js("javascript:f() onload=x") == "f()"

    def test_encode_decode_roundtrip(self):
        s = PayloadSanitizer()
        enc = s.encode({"a": 1})
        assert json.loads(base64.b64decode(enc)) == {"a": 1}
        assert s.decode(enc) == {"a": 1}

    def test_validate_types(self):
        s = PayloadSanitizer()
        assert s.validate_types("notdict") is False
        assert s.validate_types({}) is True
        assert s.validate_types({"severity": True}) is False  # bool excluded
        assert s.validate_types({"severity": 3}) is True
        assert s.validate_types({"alert_id": 5}) is False
        assert s.validate_types({"timestamp": "not-a-date"}) is False
        assert s.validate_types({"timestamp": "2024-01-01T00:00:00"}) is True


class TestTlsConfig:
    def test_verify_tls_table(self, monkeypatch):
        for v, want in [("0", False), ("false", False), ("no", False), ("off", False),
                        ("FALSE", False), (" OFF ", False),
                        ("1", True), ("yes", True), ("typo", True)]:
            monkeypatch.setenv("SVC_VERIFY_TLS", v)
            assert verify_tls("svc") is want, v

    def test_verify_tls_unset_and_default(self, monkeypatch):
        monkeypatch.delenv("SVC_VERIFY_TLS", raising=False)
        assert verify_tls("svc") is True
        assert verify_tls("svc", default=False) is False

    def test_verify_tls_full_name_and_dash(self, monkeypatch):
        monkeypatch.setenv("MISP_VERIFY_TLS", "0")
        assert verify_tls("MISP_VERIFY_TLS") is False
        assert verify_tls("misp") is False
        monkeypatch.setenv("SHUFFLE_BACKEND_VERIFY_TLS", "0")
        assert verify_tls("shuffle-backend") is False

    def test_ca_verify_repo_path(self, monkeypatch):
        # container /app paths may exist; else repo ca.crt; else default
        val = ca_verify()
        assert val is True or (isinstance(val, str) and val.endswith("ca-bundle.crt".replace("ca-bundle.crt", "") + "ca-bundle.crt") or val.endswith("ca.crt"))
        val = ca_verify(default="DEF")
        assert val == "DEF" or isinstance(val, str)


class TestBulkhead:
    def test_ctor_validation(self):
        for kw in ({"concurrent": 0}, {"queued": -1}, {"acquire_timeout": 0}):
            with pytest.raises(ValueError, match="concurrent >= 1"):
                Bulkhead("b", **kw)

    def test_full_raises(self):
        b = Bulkhead("b", concurrent=1, queued=0, acquire_timeout=0.05)
        import threading

        t = threading.Thread(target=lambda: b.run(lambda: __import__("time").sleep(0.3)))
        t.start()
        __import__("time").sleep(0.05)
        with pytest.raises(BulkheadFullError, match="bulkhead 'b' saturated"):
            b.run(lambda: None)
        t.join()

    def test_run_and_in_flight(self):
        b = Bulkhead("b", concurrent=2, queued=2)
        assert b.run(lambda: 42) == 42
        assert b.in_flight == 0

    def test_error_name_attr(self):
        e = BulkheadFullError("x")
        assert e.name == "x" and "saturated" in str(e)


class TestAsyncBulkhead:
    def test_ctor_validation(self):
        with pytest.raises(ValueError, match="concurrent >= 1"):
            AsyncBulkhead("b", concurrent=0)

    async def test_run_coroutine_and_sync(self):
        b = AsyncBulkhead("b", concurrent=1)

        async def afn():
            return 1

        assert await b.run(afn) == 1
        assert await b.run(lambda: 2) == 2

    async def test_full_raises(self):
        b = AsyncBulkhead("b", concurrent=1, queued=0, acquire_timeout=0.05)
        started = asyncio.Event()

        async def hold():
            started.set()
            await asyncio.sleep(0.3)

        task = asyncio.create_task(b.run(hold))
        await started.wait()
        with pytest.raises(BulkheadFullError):
            await b.run(lambda: None)
        await task
