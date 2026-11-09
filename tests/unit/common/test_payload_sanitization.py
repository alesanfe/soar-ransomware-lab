#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Payload Sanitization Tests
Unit tests for payload sanitization
"""

import pytest

from soar_lab.security.sanitization import PayloadSanitizer


class TestPayloadSanitization:
    """Test payload sanitization."""

    @pytest.fixture
    def sanitizer(self):
        """Create payload sanitizer for testing."""
        return PayloadSanitizer()

    def test_malicious_data_sanitization(self, sanitizer):
        """Test sanitization of malicious data."""
        malicious_payload = {
            "alert_id": "<script>alert('xss')</script>",
            "hostname": "'; DROP TABLE users; --",
            "description": "<img src=x onerror=alert(1)>",
        }

        sanitized = sanitizer.sanitize(malicious_payload)

        assert "<script>" not in sanitized["alert_id"], "Script tags should be removed"
        assert "DROP TABLE" not in sanitized["hostname"], "SQL injection should be removed"
        assert "onerror" not in sanitized["description"], "Event handlers should be removed"

    def test_encoding_decoding(self, sanitizer):
        """Test encoding and decoding."""
        original_data = {"alert_id": "TEST-001", "hostname": "test-host"}

        # Encode
        encoded = sanitizer.encode(original_data)

        # Decode
        decoded = sanitizer.decode(encoded)

        assert decoded == original_data, "Decoded data should match original"

    def test_html_sanitization(self, sanitizer):
        """Test HTML sanitization."""
        html_payload = "<div><script>alert('xss')</script><p>content</p></div>"

        sanitized = sanitizer.sanitize_html(html_payload)

        assert "<script>" not in sanitized, "Script tags should be removed"
        assert "<p>" in sanitized, "Safe HTML tags should be preserved"

    def test_js_sanitization(self, sanitizer):
        """Test JavaScript sanitization."""
        js_payload = "javascript:alert('xss')"

        sanitized = sanitizer.sanitize_js(js_payload)

        assert "javascript:" not in sanitized.lower(), "JavaScript protocol should be removed"

    def test_type_validation(self, sanitizer):
        """Test type validation."""
        invalid_payload = {
            "alert_id": 123,  # Should be string
            "severity": "high",  # Should be integer
            "timestamp": "invalid-date",
        }

        is_valid = sanitizer.validate_types(invalid_payload)
        assert not is_valid, "Invalid types should be rejected"

    def test_null_byte_removal(self, sanitizer):
        """Test null byte removal."""
        payload_with_nulls = {"alert_id": "TEST\x00-001", "hostname": "host\x00name"}

        sanitized = sanitizer.sanitize(payload_with_nulls)

        assert "\x00" not in sanitized["alert_id"], "Null bytes should be removed"
        assert "\x00" not in sanitized["hostname"], "Null bytes should be removed"

    def test_control_character_removal(self, sanitizer):
        """Control chars in the strip set are actually removed from output."""
        payload_with_controls = {"alert_id": "TEST\x01\x02-001", "hostname": "host\x1fname"}

        sanitized = sanitizer.sanitize(payload_with_controls)

        assert "\x01" not in sanitized["alert_id"]
        assert "\x02" not in sanitized["alert_id"]
        assert "\x1f" not in sanitized["hostname"]
        assert "TEST" in sanitized["alert_id"]

    def test_unicode_normalization(self, sanitizer):
        """Compatibility decomposition is folded by NFKC."""
        # ﬁ (U+FB01 LATIN SMALL LIGATURE FI) normalizes to "fi" under NFKC
        unicode_payload = {"alert_id": "ﬁle-name"}

        sanitized = sanitizer.sanitize(unicode_payload)

        assert sanitized["alert_id"] == "file-name"

    def test_max_length_enforcement(self, sanitizer):
        """Test max length enforcement."""
        long_payload = {"alert_id": "A" * 1000, "hostname": "B" * 1000}

        sanitized = sanitizer.sanitize(long_payload, max_length=100)

        assert len(sanitized["alert_id"]) <= 100, "Alert ID should be truncated"
        assert len(sanitized["hostname"]) <= 100, "Hostname should be truncated"

    def test_sanitize_html_max_length_truncates(self, sanitizer):
        assert len(sanitizer.sanitize_html("<p>" + "x" * 500 + "</p>", max_length=50)) <= 50

    def test_sanitize_js_max_length_truncates(self, sanitizer):
        assert len(sanitizer.sanitize_js("x" * 500, max_length=50)) <= 50

    def test_validate_types_non_dict_returns_false(self, sanitizer):
        assert sanitizer.validate_types("not a dict") is False
        assert sanitizer.validate_types([1, 2]) is False

    def test_validate_types_missing_field_skipped(self, sanitizer):
        # None values are optional — only present fields are checked.
        assert sanitizer.validate_types({"alert_id": "a1"}) is True

    def test_validate_types_bool_is_not_int(self, sanitizer):
        # bool is a subclass of int — must NOT be accepted as severity.
        assert sanitizer.validate_types({"severity": True}) is False
        assert sanitizer.validate_types({"severity": 5}) is True

    def test_validate_types_str_fields_reject_non_str(self, sanitizer):
        assert sanitizer.validate_types({"alert_id": 42}) is False

    def test_validate_types_timestamp_must_parse_iso(self, sanitizer):
        assert sanitizer.validate_types({"timestamp": "not-a-date"}) is False
        assert sanitizer.validate_types({"timestamp": "2026-01-01T00:00:00"}) is True

    def test_field_whitelist(self, sanitizer):
        """Test field whitelist."""
        payload = {
            "alert_id": "TEST-001",
            "hostname": "test-host",
            "malicious_field": "should_be_removed",
        }

        whitelist = ["alert_id", "hostname"]
        sanitized = sanitizer.sanitize(payload, whitelist=whitelist)

        assert "alert_id" in sanitized, "Whitelisted field should be preserved"
        assert "hostname" in sanitized, "Whitelisted field should be preserved"
        assert "malicious_field" not in sanitized, "Non-whitelisted field should be removed"

    def test_field_blacklist(self, sanitizer):
        """Test field blacklist."""
        payload = {"alert_id": "TEST-001", "hostname": "test-host", "password": "secret123"}

        blacklist = ["password", "api_key"]
        sanitized = sanitizer.sanitize(payload, blacklist=blacklist)

        assert "alert_id" in sanitized, "Non-blacklisted field should be preserved"
        assert "password" not in sanitized, "Blacklisted field should be removed"

    def test_whitelist_preserves_nested_payload(self, sanitizer):
        """Bug: whitelist was applied recursively — a nested dict under a
        whitelisted key had ALL its keys stripped (data loss)."""
        payload = {
            "alert_id": "TEST-001",
            "data": {"hash": "abc123", "ip": "10.0.0.1"},
            "malicious_field": "x",
        }
        sanitized = sanitizer.sanitize(payload, whitelist=["alert_id", "data"])
        assert sanitized["data"] == {"hash": "abc123", "ip": "10.0.0.1"}

    def test_blacklist_removes_nested_keys(self, sanitizer):
        """Blacklist SHOULD stay recursive (strip secrets at any depth)."""
        payload = {"alert_id": "A", "data": {"password": "secret", "ok": 1}}
        sanitized = sanitizer.sanitize(payload, blacklist=["password"])
        assert sanitized["data"] == {"ok": 1}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestSanitizerMutationHardening:
    """Exact-output assertions killing sub()/arg/boundary survivors."""

    def test_list_items_inherit_blacklist(self):
        s = PayloadSanitizer()
        out = s.sanitize([{"secret": "x", "keep": "y"}], blacklist=["secret"])
        assert out == [{"keep": "y"}]

    def test_list_items_inherit_max_length(self):
        s = PayloadSanitizer()
        out = s.sanitize(["a" * 100], max_length=5)
        assert out == ["aaaaa"]

    def test_list_of_strings_each_sanitized(self):
        s = PayloadSanitizer()
        out = s.sanitize(["<script>bad()</script>ok", "fine"])
        assert out == ["ok", "fine"]

    def test_nested_dict_inside_list(self):
        s = PayloadSanitizer()
        out = s.sanitize([{"a": {"b": "<script>x</script>hi"}}])
        assert out == [{"a": {"b": "hi"}}]

    def test_script_tag_removed_not_replaced(self):
        s = PayloadSanitizer()
        assert s.sanitize("pre<script>alert(1)</script>post") == "prepost"

    def test_null_byte_removed_exactly(self):
        s = PayloadSanitizer()
        assert s.sanitize("a\x00b") == "ab"

    def test_control_chars_removed_exactly(self):
        s = PayloadSanitizer()
        assert s.sanitize("a\x01b\x1fc\x7f") == "abc"

    def test_drop_table_removed_exactly(self):
        s = PayloadSanitizer()
        assert s.sanitize("x DROP TABLE y") == "x  y"

    def test_on_event_removed_exactly(self):
        s = PayloadSanitizer()
        assert s.sanitize("<img src=x onerror=alert(1)>") == "<img src=x>"

    def test_js_protocol_removed_exactly(self):
        s = PayloadSanitizer()
        assert s.sanitize_js("javascript:alert(1)") == "alert(1)"
        assert s.sanitize("<a href=javascript:evil()>x</a>") == "<a href=evil()>x</a>"

    def test_fixpoint_removal_recursive_pattern(self):
        s = PayloadSanitizer()
        # "<scr<script></script>ipt>" strips inner script tag leaving "<script>"
        assert s.sanitize("<scr<script></script>ipt>x</script>") == ""

    def test_exact_max_length_not_truncated(self):
        s = PayloadSanitizer()
        v = "a" * 10
        assert s.sanitize(v, max_length=10) == "a" * 10
        assert s.sanitize_html(v, max_length=10) == "a" * 10
        assert s.sanitize_js(v, max_length=10) == "a" * 10

    def test_max_length_plus_one_truncated(self):
        s = PayloadSanitizer()
        assert s.sanitize("a" * 11, max_length=10) == "a" * 10
        assert s.sanitize_html("a" * 11, max_length=10) == "a" * 10
        assert s.sanitize_js("a" * 11, max_length=10) == "a" * 10

    def test_sanitize_html_keeps_safe_markup(self):
        s = PayloadSanitizer()
        assert s.sanitize_html("<b>bold</b>") == "<b>bold</b>"
        assert s.sanitize_html("<div onclick=x>y</div>") == "<div>y</div>"

    def test_encode_decode_round_trip_exact(self):
        s = PayloadSanitizer()
        payload = {"a": "x", "n": 1}
        enc = s.encode(payload)
        assert isinstance(enc, str) and "x" not in enc
        assert s.decode(enc) == payload

    def test_sanitize_js_on_event_removed(self):
        s = PayloadSanitizer()
        assert s.sanitize_js("x onclick=evil()") == "x"
        assert s.sanitize_js("a onload=do() b") == "a b"

    def test_sanitize_dict_whitelist_continues_not_breaks(self):
        s = PayloadSanitizer()
        # "bad" first: `continue` skips it, `break` would lose "good" too
        r = s.sanitize({"bad": 1, "good": 2}, whitelist=["good"])
        assert r == {"good": 2}

    def test_sanitize_dict_blacklist_continues_not_breaks(self):
        s = PayloadSanitizer()
        r = s.sanitize({"bad": 1, "good": 2}, blacklist=["bad"])
        assert r == {"good": 2}

    def test_sanitize_html_script_tag_removed(self):
        s = PayloadSanitizer()
        assert s.sanitize_html("<script>alert(1)</script>ok") == "ok"
