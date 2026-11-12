"""HMAC-001..006 + SEC-002: transport & envelope signature tests.

Positive, negative and adversarial cases — every rejection path of
``verify_request``/``verify_envelope`` is exercised.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from soar_lab.security.webhook_signing import (
    InMemoryNonceStore,
    RedisNonceStore,
    ReplayError,
    SignatureError,
    _bounded,
    body_sha256,
    canonical_request,
    sign_envelope,
    sign_request,
    verify_envelope,
    verify_request,
)

SECRET = "unit-test-secret-key-0123456789abcdef"
KEY_ID = "api-forward-1"


def _resolver(secret=SECRET):
    return lambda key_id: secret if key_id == KEY_ID else None


def _body() -> bytes:
    return b'{"alert_id":"alr-1","severity":3}'


class TestTransportSignature:
    async def test_roundtrip(self):
        headers = sign_request(
            SECRET, method="POST", path="/api/v1/alerts/callback", body=_body(), key_id=KEY_ID
        )
        result = await verify_request(
            _resolver(),
            method="POST",
            path="/api/v1/alerts/callback",
            headers=headers,
            body=_body(),
            nonce_store=InMemoryNonceStore(),
        )
        assert result["key_id"] == KEY_ID

    async def test_tampered_body_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        with pytest.raises(SignatureError):
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=b"{}"
            )

    async def test_tampered_path_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        with pytest.raises(SignatureError):
            await verify_request(
                _resolver(), method="POST", path="/other", headers=headers, body=_body()
            )

    async def test_stale_timestamp_rejected(self):
        old = time.time() - 4000
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID, now=old
        )
        with pytest.raises(SignatureError):
            await verify_request(_resolver(), method="POST", path="/cb", headers=headers, body=_body())

    async def test_future_timestamp_rejected(self):
        future = time.time() + 4000
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID, now=future
        )
        with pytest.raises(SignatureError):
            await verify_request(_resolver(), method="POST", path="/cb", headers=headers, body=_body())

    async def test_nonce_replay_rejected(self):
        store = InMemoryNonceStore()
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        await verify_request(
            _resolver(), method="POST", path="/cb", headers=headers, body=_body(), nonce_store=store
        )
        with pytest.raises(ReplayError):
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=_body(), nonce_store=store
            )

    async def test_unknown_key_id_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id="evil-key"
        )
        with pytest.raises(SignatureError):
            await verify_request(_resolver(), method="POST", path="/cb", headers=headers, body=_body())

    async def test_alg_v2_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        headers["X-SOAR-Signature-Version"] = "v2"
        with pytest.raises(SignatureError):
            await verify_request(_resolver(), method="POST", path="/cb", headers=headers, body=_body())

    async def test_missing_signature_rejected(self):
        with pytest.raises(SignatureError):
            await verify_request(_resolver(), method="POST", path="/cb", headers={}, body=_body())

    async def test_oversized_header_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        headers["X-SOAR-Signature"] = "v1=" + "a" * 900
        with pytest.raises(SignatureError):
            await verify_request(_resolver(), method="POST", path="/cb", headers=headers, body=_body())


class TestEnvelopeSignature:
    def test_roundtrip(self):
        payload = {"severity": 3, "alert_id": "alr-1"}
        signed = sign_envelope(payload, SECRET, key_id=KEY_ID)
        assert verify_envelope(signed, _resolver())["key_id"] == KEY_ID

    def test_tampered_field_rejected(self):
        signed = sign_envelope({"severity": 3}, SECRET, key_id=KEY_ID)
        signed["severity"] = 4
        with pytest.raises(SignatureError):
            verify_envelope(signed, _resolver())

    def test_tampered_signature_rejected(self):
        signed = sign_envelope({"severity": 3}, SECRET, key_id=KEY_ID)
        signed["security"]["signature"] = "0" * 64
        with pytest.raises(SignatureError):
            verify_envelope(signed, _resolver())

    def test_stale_envelope_rejected(self):
        signed = sign_envelope({"severity": 3}, SECRET, key_id=KEY_ID, now=time.time() - 4000)
        with pytest.raises(SignatureError):
            verify_envelope(signed, _resolver())

    def test_missing_envelope_rejected(self):
        with pytest.raises(SignatureError):
            verify_envelope({"severity": 3}, _resolver())

    def test_wrong_key_rejected(self):
        signed = sign_envelope({"severity": 3}, "other-secret", key_id=KEY_ID)
        with pytest.raises(SignatureError):
            verify_envelope(signed, _resolver())


class TestMissingBranches:
    async def test_malformed_timestamp_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        headers["X-SOAR-Timestamp"] = "not-a-number"
        with pytest.raises(SignatureError, match="timestamp malformed"):
            await verify_request(
                _resolver(), method="POST", path="/cb",
                headers=headers, body=_body(),
            )

    async def test_expired_nonce_swept(self):
        store = InMemoryNonceStore()
        store._nonces["old"] = time.time() - 10  # already expired
        assert await store.claim("old") is True  # swept then claimed

    async def test_redis_nonce_claim_and_failure(self):
        from soar_lab.security.webhook_signing import RedisNonceStore

        class Redis:
            async def set(self, *a, **kw):
                return True

        assert await RedisNonceStore(Redis()).claim("n") is True

        class DeadRedis:
            async def set(self, *a, **kw):
                raise RuntimeError("down")

        with pytest.raises(SignatureError, match="nonce store unavailable"):
            await RedisNonceStore(DeadRedis()).claim("n")

    async def test_headers_without_items_rejected(self):
        with pytest.raises(SignatureError):
            await verify_request(
                _resolver(), method="POST", path="/cb",
                headers=[("x", "y")], body=_body(),  # list has no .items
            )

    async def test_tuple_resolver_grace(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        result = await verify_request(
            lambda kid: (SECRET, True) if kid == KEY_ID else None,
            method="POST", path="/cb", headers=headers, body=_body(),
        )
        assert result["rotation_grace"] is True

    async def test_bad_signature_scheme_rejected(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=_body(), key_id=KEY_ID
        )
        headers["X-SOAR-Signature"] = "v9=" + "0" * 64
        with pytest.raises(SignatureError, match="not allowed"):
            await verify_request(
                _resolver(), method="POST", path="/cb",
                headers=headers, body=_body(),
            )


class TestEnvelopeMissingBranches:
    def test_envelope_not_dict(self):
        with pytest.raises(SignatureError, match="missing security"):
            verify_envelope({"security": "nope"}, _resolver())

    def test_envelope_bad_alg(self):
        with pytest.raises(SignatureError, match="alg not allowed"):
            verify_envelope({"security": {"alg": "v9"}}, _resolver())

    def test_envelope_missing_key_id(self):
        with pytest.raises(SignatureError, match="missing key id"):
            verify_envelope({"security": {"alg": "v1"}}, _resolver())

    def test_envelope_unknown_key(self):
        with pytest.raises(SignatureError, match="unknown key"):
            verify_envelope(
                {"security": {"alg": "v1", "key_id": "nope"}}, _resolver()
            )

    def test_envelope_tuple_resolver(self):
        msg = {"alert_id": "a1"}
        env = sign_envelope(dict(msg), SECRET, key_id=KEY_ID)
        out = verify_envelope(
            env, lambda kid: (SECRET, True) if kid == KEY_ID else None
        )
        assert out["key_id"] == KEY_ID

    def test_envelope_malformed_timestamp(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["security"]["timestamp"] = "garbage"
        with pytest.raises(SignatureError, match="timestamp malformed"):
            verify_envelope(env, _resolver())


class TestExactErrorContracts:
    """Assert exact codes/messages/dicts — kills XX string mutants."""

    def test_signature_error_default_code_and_message(self):
        e = SignatureError("boom")
        assert e.code == "SIGNATURE_INVALID"
        assert str(e) == "boom"

    def test_replay_error_contract(self):
        e = ReplayError()
        assert e.code == "REPLAY_DETECTED"
        assert str(e) == "nonce already used"

    def test_canonical_request_format(self):
        c = canonical_request("post", "/p", "1", "n", "s")
        assert c == "POST\n/p\n1\nn\ns"

    def test_mac_accepts_bytes_secret(self):
        from soar_lab.security.webhook_signing import _mac

        assert _mac(b"k", "c") == _mac("k", "c")

    def test_sign_request_exact_header_names(self):
        h = sign_request(
            SECRET, method="POST", path="/p", body=b"x", key_id=KEY_ID, now=1
        )
        assert set(h) == {
            "X-SOAR-Signature-Version",
            "X-SOAR-Key-Id",
            "X-SOAR-Timestamp",
            "X-SOAR-Nonce",
            "X-SOAR-Content-SHA256",
            "X-SOAR-Signature",
        }
        assert h["X-SOAR-Signature-Version"] == "v1"
        assert h["X-SOAR-Key-Id"] == KEY_ID
        assert h["X-SOAR-Timestamp"] == "1"
        assert h["X-SOAR-Signature"].startswith("v1=")

    def test_missing_field_exact_messages(self):
        with pytest.raises(SignatureError) as ei:
            _bounded(None, "field x")
        assert str(ei.value) == "missing field x"
        assert ei.value.code == "SIGNATURE_MISSING"

    def test_too_long_exact(self):
        with pytest.raises(SignatureError) as ei:
            _bounded("y" * 513, "field x")
        assert str(ei.value) == "field x too long"
        assert ei.value.code == "SIGNATURE_MALFORMED"

    def test_freshness_boundary_and_codes(self):
        from soar_lab.security.webhook_signing import _check_freshness

        _check_freshness("100", 300, now=400.0)  # boundary == skew is OK
        with pytest.raises(SignatureError) as ei:
            _check_freshness("99", 300, now=400.0)
        assert str(ei.value) == "timestamp outside acceptance window"
        assert ei.value.code == "SIGNATURE_STALE"
        with pytest.raises(SignatureError) as ei2:
            _check_freshness("abc", 300, now=400.0)
        assert str(ei2.value) == "timestamp malformed"
        assert ei2.value.code == "SIGNATURE_MALFORMED"

    async def test_verify_request_alg_code(self):
        headers = {
            "X-SOAR-Signature-Version": "v9",
            "X-SOAR-Key-Id": KEY_ID,
            "X-SOAR-Timestamp": str(int(time.time())),
            "X-SOAR-Nonce": "n",
            "X-SOAR-Content-SHA256": "0" * 64,
            "X-SOAR-Signature": "v1=" + "0" * 64,
        }
        with pytest.raises(SignatureError) as ei:
            await verify_request(
                _resolver(), method="POST", path="/p", headers=headers, body=b""
            )
        assert str(ei.value) == "signature version not allowed"
        assert ei.value.code == "SIGNATURE_ALG"

    async def test_verify_request_unknown_key_code(self):
        h = sign_request(
            SECRET, method="POST", path="/p", body=b"{}", key_id="other", now=1
        )
        with pytest.raises(SignatureError) as ei:
            await verify_request(
                _resolver(), method="POST", path="/p", headers=h, body=b"{}"
            )
        assert str(ei.value) == "unknown key id"
        assert ei.value.code == "SIGNATURE_UNKNOWN_KEY"

    async def test_verify_request_sig_mismatch_default_code(self):
        h = sign_request(
            SECRET, method="POST", path="/p", body=b"{}", key_id=KEY_ID
        )
        h["X-SOAR-Signature"] = "v1=" + "0" * 64
        with pytest.raises(SignatureError) as ei:
            await verify_request(
                _resolver(), method="POST", path="/p", headers=h, body=b"{}"
            )
        assert str(ei.value) == "signature mismatch"
        assert ei.value.code == "SIGNATURE_INVALID"

    async def test_verify_request_rotation_grace_tuple(self):
        h = sign_request(
            "oldsecret", method="POST", path="/p", body=b"{}", key_id="prev-id"
        )
        r = await verify_request(
            lambda kid: ("oldsecret", True), method="POST", path="/p",
            headers=h, body=b"{}",
        )
        assert r == {"key_id": "prev-id", "rotation_grace": True}

    def test_envelope_missing_code(self):
        with pytest.raises(SignatureError) as ei:
            verify_envelope({"a": 1}, _resolver())
        assert str(ei.value) == "missing security envelope"
        assert ei.value.code == "SIGNATURE_MISSING"

    def test_envelope_alg_code(self):
        with pytest.raises(SignatureError) as ei:
            verify_envelope({"security": {"alg": "v9"}}, _resolver())
        assert str(ei.value) == "envelope alg not allowed"
        assert ei.value.code == "SIGNATURE_ALG"

    def test_envelope_missing_key_id_code(self):
        with pytest.raises(SignatureError) as ei:
            verify_envelope({"security": {"alg": "v1"}}, _resolver())
        assert str(ei.value) == "missing key id"
        assert ei.value.code == "SIGNATURE_MALFORMED"

    def test_envelope_unknown_key_code(self):
        with pytest.raises(SignatureError) as ei:
            verify_envelope(
                {"security": {"alg": "v1", "key_id": "zzz"}}, _resolver()
            )
        assert str(ei.value) == "unknown key id"
        assert ei.value.code == "SIGNATURE_UNKNOWN_KEY"

    def test_envelope_stale_boundary(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID, now=1000)
        verify_envelope(env, _resolver(), skew_s=300, now=1300.0)  # diff==skew ok
        env2 = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID, now=999)
        with pytest.raises(SignatureError) as ei:
            verify_envelope(env2, _resolver(), skew_s=300, now=1300.0)
        assert str(ei.value) == "envelope timestamp stale"
        assert ei.value.code == "SIGNATURE_STALE"

    def test_envelope_malformed_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["security"]["timestamp"] = None
        with pytest.raises(SignatureError) as ei:
            verify_envelope(env, _resolver())
        assert str(ei.value) == "envelope timestamp malformed"
        assert ei.value.code == "SIGNATURE_MALFORMED"

    def test_envelope_body_digest_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["security"]["payload_sha256"] = "0" * 64
        with pytest.raises(SignatureError) as ei:
            verify_envelope(env, _resolver())
        assert str(ei.value) == "payload digest mismatch"
        assert ei.value.code == "SIGNATURE_BODY"

    def test_envelope_sig_mismatch_default_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["security"]["signature"] = "0" * 64
        with pytest.raises(SignatureError) as ei:
            verify_envelope(env, _resolver())
        assert str(ei.value) == "envelope signature mismatch"
        assert ei.value.code == "SIGNATURE_INVALID"

    def test_envelope_return_dict_exact(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        out = verify_envelope(env, _resolver())
        assert set(out) == {"key_id", "nonce"}
        assert out["key_id"] == KEY_ID
        assert out["nonce"] == env["security"]["nonce"]

    def test_envelope_missing_sha_fields_raise_body(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        del env["security"]["payload_sha256"]
        with pytest.raises(SignatureError):
            verify_envelope(env, _resolver())

    def test_envelope_missing_signature_field(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        del env["security"]["signature"]
        with pytest.raises(SignatureError, match="signature mismatch"):
            verify_envelope(env, _resolver())

    async def test_inmemory_nonce_replay_and_expiry(self):
        store = InMemoryNonceStore()
        assert await store.claim("n1") is True
        assert await store.claim("n1") is False
        store._nonces["old"] = time.time() - 10
        assert await store.claim("old") is True

    async def test_redis_nonce_store_down_error(self):
        class BadRedis:
            async def set(self, *a, **kw):
                raise RuntimeError("down")

        with pytest.raises(SignatureError) as ei:
            await RedisNonceStore(BadRedis()).claim("n")
        assert str(ei.value) == "nonce store unavailable"
        assert ei.value.code == "NONCE_STORE_DOWN"

    async def test_redis_nonce_store_won_and_lost(self):
        class R:
            def __init__(self, won):
                self.won = won
                self.kw = None

            async def set(self, *a, **kw):
                self.kw = kw
                return self.won

        r = R(True)
        assert await RedisNonceStore(r).claim("abc", ttl_s=5) is True
        assert r.kw.get("ex") == 5
        assert await RedisNonceStore(R(False)).claim("abc") is False

    def test_sign_envelope_fields(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID, now=42)
        sec = env["security"]
        assert sec["alg"] == "v1"
        assert sec["key_id"] == KEY_ID
        assert sec["timestamp"] == 42
        assert len(sec["nonce"]) == 32
        assert len(sec["payload_sha256"]) == 64
        assert len(sec["signature"]) == 64


