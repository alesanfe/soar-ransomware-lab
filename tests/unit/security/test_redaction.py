"""ERROR-001/002 + B6: capability URL and secrets never reach text sinks."""

from __future__ import annotations

from soar_lab.security.redaction import redact_text, redact_url, safe_error

HOOK = "https://shuffle-backend:5443/api/v1/hooks/webhook_01234567-89ab-cdef-0123-456789abcdef"


class TestRedactText:
    def test_hook_url_redacted(self):
        out = redact_text(f"Connection to {HOOK} refused")
        assert "webhook_" not in out
        assert "01234567" not in out

    def test_bearer_redacted(self):
        assert "tok" not in redact_text("Bearer tok_abcdefghij12345678").lower() or "[redacted]" in redact_text("Bearer tok_abcdefghij12345678")

    def test_token_kv_redacted(self):
        out = redact_text("error token=supersecretvalue123")
        assert "supersecretvalue123" not in out

    def test_query_string_redacted(self):
        out = redact_text("GET http://h/p?api_key=abc123 failed")
        assert "api_key=abc123" not in out

    def test_control_chars_stripped(self):
        out = redact_text("line1\nFORGED: line2")
        assert "\n" not in out

    def test_max_len(self):
        assert len(redact_text("x" * 500, max_len=50)) <= 51


class TestRedactUrl:
    def test_only_origin_kept(self):
        out = redact_url(HOOK)
        assert out == "https://shuffle-backend:5443"
        assert "webhook" not in out

    def test_bad_url(self):
        assert "unknown" in redact_url("not a url") or "redacted" in redact_url("not a url")


class TestSafeError:
    def test_structured_no_url(self):
        err = safe_error(Exception(f"POST {HOOK} timed out"), code="DOWNSTREAM_TIMEOUT", retryable=True)
        assert err["code"] == "DOWNSTREAM_TIMEOUT"
        assert "webhook_" not in err["message"]
        assert err["retryable"] is True


def test_redact_text_none_returns_empty():
    assert redact_text(None) == ""


def test_redact_url_unparseable_returns_placeholder():
    # a bad port makes urlsplit raise on .port access -> except branch
    assert redact_url("http://host:notaport/x") == "[redacted-url]"
