"""Exact-contract tests for webhook_signing — kills mutation classes the
behavioural suite leaves alive: error codes, message text, header names,
canonical formats, Redis claim args and boundary values.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock

import pytest

from soar_lab.security import webhook_signing as ws
from soar_lab.security.webhook_signing import (
    InMemoryNonceStore,
    RedisNonceStore,
    ReplayError,
    SignatureError,
    body_sha256,
    canonical_request,
    sign_envelope,
    sign_request,
    verify_envelope,
    verify_request,
)

SECRET = "contract-secret-key-0123456789abcdef"
KEY_ID = "api-forward-1"


def _resolver(secret=SECRET):
    return lambda key_id: secret if key_id == KEY_ID else None


class TestConstants:
    def test_versions_and_windows(self):
        assert ws.SIGNATURE_VERSION == "v1"
        assert ws.DEFAULT_SKEW_S == 300
        assert ws.NONCE_TTL_S == 660
        assert ws._MAX_HEADER_LEN == 512
        assert ws._ALLOWED_ALGS == {"v1"}
        assert ws._ENVELOPE_KEY == "security"

    def test_header_names(self):
        assert ws.HDR_VERSION == "x-soar-signature-version"
        assert ws.HDR_KEY_ID == "x-soar-key-id"
        assert ws.HDR_TIMESTAMP == "x-soar-timestamp"
        assert ws.HDR_NONCE == "x-soar-nonce"
        assert ws.HDR_CONTENT_SHA == "x-soar-content-sha256"
        assert ws.HDR_SIGNATURE == "x-soar-signature"


class TestExceptions:
    def test_signature_error_defaults(self):
        exc = SignatureError("detail")
        assert str(exc) == "detail"
        assert exc.code == "SIGNATURE_INVALID"

    def test_replay_error_contract(self):
        exc = ReplayError()
        assert isinstance(exc, SignatureError)
        assert str(exc) == "nonce already used"
        assert exc.code == "REPLAY_DETECTED"


class TestCanonical:
    def test_body_sha256_golden(self):
        assert body_sha256(b"abc") == hashlib.sha256(b"abc").hexdigest()

    def test_canonical_request_format(self):
        assert canonical_request("post", "/p", "123", "n", "s") == "POST\n/p\n123\nn\ns"

    def test_canonical_request_method_uppercased(self):
        assert canonical_request("get", "/x", "0", "n", "s").startswith("GET\n")

    def test_mac_accepts_bytes_secret(self):
        a = ws._mac(SECRET, "x")
        b = ws._mac(SECRET.encode(), "x")
        assert a == b == hmac.new(SECRET.encode(), b"x", hashlib.sha256).hexdigest()

    def test_canonical_payload_sorted_and_compact(self):
        out = ws._canonical_payload({"b": 1, "a": {"z": 2, "y": 3}})
        assert out == b'{"a":{"y":3,"z":2},"b":1}'


class TestBounded:
    def test_missing_raises_missing_code(self):
        with pytest.raises(SignatureError) as e:
            ws._bounded(None, "nonce")
        assert e.value.code == "SIGNATURE_MISSING"
        assert str(e.value) == "missing nonce"

    def test_empty_raises_missing_code(self):
        with pytest.raises(SignatureError) as e:
            ws._bounded("", "nonce")
        assert e.value.code == "SIGNATURE_MISSING"

    def test_oversized_raises_malformed_code(self):
        with pytest.raises(SignatureError) as e:
            ws._bounded("x" * 513, "nonce")
        assert e.value.code == "SIGNATURE_MALFORMED"
        assert str(e.value) == "nonce too long"

    def test_exactly_max_len_ok(self):
        assert ws._bounded("x" * 512, "nonce") == "x" * 512


class TestFreshness:
    def test_non_numeric_timestamp(self):
        with pytest.raises(SignatureError) as e:
            ws._check_freshness("abc", 300, 1000.0)
        assert e.value.code == "SIGNATURE_MALFORMED"
        assert str(e.value) == "timestamp malformed"

    def test_stale_timestamp(self):
        with pytest.raises(SignatureError) as e:
            ws._check_freshness("100", 300, 1000.0)
        assert e.value.code == "SIGNATURE_STALE"
        assert str(e.value) == "timestamp outside acceptance window"

    def test_boundary_skew_accepted(self):
        ws._check_freshness("700", 300, 1000.0)  # exactly 300s old
        ws._check_freshness("1300", 300, 1000.0)  # 300s in the future


class TestSignRequestContract:
    def test_header_set_and_values(self):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID, now=1700000000.9
        )
        assert set(headers) == {
            "X-SOAR-Signature-Version",
            "X-SOAR-Key-Id",
            "X-SOAR-Timestamp",
            "X-SOAR-Nonce",
            "X-SOAR-Content-SHA256",
            "X-SOAR-Signature",
        }
        assert headers["X-SOAR-Signature-Version"] == "v1"
        assert headers["X-SOAR-Key-Id"] == KEY_ID
        assert headers["X-SOAR-Timestamp"] == "1700000000"  # int-truncated
        assert len(headers["X-SOAR-Nonce"]) == 32  # uuid4 hex
        assert headers["X-SOAR-Content-SHA256"] == body_sha256(body)
        sig = headers["X-SOAR-Signature"]
        assert sig.startswith("v1=")
        canonical = canonical_request(
            "POST", "/cb", "1700000000", headers["X-SOAR-Nonce"], body_sha256(body)
        )
        expected = hmac.new(SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        assert sig == f"v1={expected}"


class TestVerifyRequestContract:
    async def test_success_return_shape(self):
        body = b'{"a":1}'
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        res = await verify_request(
            _resolver(), method="POST", path="/cb", headers=headers, body=body
        )
        assert res == {"key_id": KEY_ID, "rotation_grace": False}

    async def test_tuple_resolver_marks_grace(self):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        res = await verify_request(
            lambda k: (SECRET, True), method="POST", path="/cb", headers=headers, body=body
        )
        assert res == {"key_id": KEY_ID, "rotation_grace": True}

    @pytest.mark.parametrize(
        "missing,needle",
        [
            ("X-SOAR-Signature-Version", "signature version"),
            ("X-SOAR-Key-Id", "key id"),
            ("X-SOAR-Timestamp", "timestamp"),
            ("X-SOAR-Nonce", "nonce"),
            ("X-SOAR-Content-SHA256", "content sha"),
            ("X-SOAR-Signature", "signature"),
        ],
    )
    async def test_missing_header_codes(self, missing, needle):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        del headers[missing]
        with pytest.raises(SignatureError) as e:
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=body
            )
        assert e.value.code == "SIGNATURE_MISSING"
        assert str(e.value) == f"missing {needle}"

    async def test_unknown_version_code(self):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        headers["X-SOAR-Signature-Version"] = "v2"
        with pytest.raises(SignatureError) as e:
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=body
            )
        assert e.value.code == "SIGNATURE_ALG"
        assert str(e.value) == "signature version not allowed"

    async def test_unknown_key_code(self):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        with pytest.raises(SignatureError) as e:
            await verify_request(
                lambda k: None,
                method="POST",
                path="/cb",
                headers=headers,
                body=body,
            )
        assert e.value.code == "SIGNATURE_UNKNOWN_KEY"
        assert str(e.value) == "unknown key id"

    async def test_body_digest_mismatch_code(self):
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=b"{}", key_id=KEY_ID
        )
        with pytest.raises(SignatureError) as e:
            await verify_request(
                _resolver(),
                method="POST",
                path="/cb",
                headers=headers,
                body=b'{"different":true}',
            )
        assert e.value.code == "SIGNATURE_BODY"
        assert str(e.value) == "content digest mismatch"

    async def test_signature_scheme_alg_code(self):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        headers["X-SOAR-Signature"] = "v2=deadbeef"
        with pytest.raises(SignatureError) as e:
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=body
            )
        assert e.value.code == "SIGNATURE_ALG"
        assert str(e.value) == "signature version/alg not allowed"

    async def test_signature_mismatch_default_code(self):
        body = b"{}"
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        headers["X-SOAR-Signature"] = "v1=" + "0" * 64
        with pytest.raises(SignatureError) as e:
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=body
            )
        assert e.value.code == "SIGNATURE_INVALID"
        assert str(e.value) == "signature mismatch"

    async def test_replay_raises_replay_error(self):
        body = b"{}"
        store = InMemoryNonceStore()
        headers = sign_request(
            SECRET, method="POST", path="/cb", body=body, key_id=KEY_ID
        )
        await verify_request(
            _resolver(), method="POST", path="/cb", headers=headers, body=body,
            nonce_store=store,
        )
        with pytest.raises(ReplayError) as e:
            await verify_request(
                _resolver(), method="POST", path="/cb", headers=headers, body=body,
                nonce_store=store,
            )
        assert e.value.code == "REPLAY_DETECTED"
        assert str(e.value) == "nonce already used"


class TestNonceStores:
    async def test_in_memory_first_wins_then_rejects(self):
        store = InMemoryNonceStore()
        assert await store.claim("n1") is True
        assert await store.claim("n1") is False

    async def test_redis_claim_set_args(self):
        client = AsyncMock()
        client.set = AsyncMock(return_value=True)
        store = RedisNonceStore(client)
        assert await store.claim("abc") is True
        client.set.assert_awaited_once_with("soar:nonce:abc", "1", nx=True, ex=660)

    async def test_redis_claim_lost_returns_false(self):
        client = AsyncMock()
        client.set = AsyncMock(return_value=None)
        store = RedisNonceStore(client)
        assert await store.claim("abc") is False

    async def test_redis_claim_failure_raises(self):
        client = AsyncMock()
        client.set = AsyncMock(side_effect=RuntimeError("down"))
        store = RedisNonceStore(client)
        with pytest.raises(SignatureError) as e:
            await store.claim("abc")
        assert e.value.code == "NONCE_STORE_DOWN"
        assert str(e.value) == "nonce store unavailable"

    def test_redis_key_prefix(self):
        assert RedisNonceStore.KEY_PREFIX == "soar:nonce:"


class TestEnvelopeContract:
    def test_sign_envelope_security_block(self):
        out = sign_envelope({"a": 1, "b": "x"}, SECRET, key_id=KEY_ID, now=1700000000)
        sec = out["security"]
        assert set(sec) == {"alg", "key_id", "timestamp", "nonce", "payload_sha256", "signature"}
        assert sec["alg"] == "v1"
        assert sec["key_id"] == KEY_ID
        assert sec["timestamp"] == 1700000000
        assert len(sec["nonce"]) == 32
        digest = hashlib.sha256(json.dumps({"a": 1, "b": "x"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        assert sec["payload_sha256"] == digest
        expected = hmac.new(
            SECRET.encode(), f"v1|1700000000|{sec['nonce']}|{digest}".encode(), hashlib.sha256
        ).hexdigest()
        assert sec["signature"] == expected

    def test_sign_envelope_strips_prior_security(self):
        first = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID, now=1)
        second = sign_envelope(first, SECRET, key_id=KEY_ID, now=1)
        # re-signing an already-signed payload covers only the clean fields
        assert verify_envelope(second, _resolver(), now=1)["key_id"] == KEY_ID

    def test_verify_envelope_success_shape(self):
        out = sign_envelope({"x": 2}, SECRET, key_id=KEY_ID)
        res = verify_envelope(out, _resolver())
        assert res == {"key_id": KEY_ID, "nonce": out["security"]["nonce"]}

    def test_missing_envelope_code(self):
        with pytest.raises(SignatureError) as e:
            verify_envelope({"a": 1}, _resolver())
        assert e.value.code == "SIGNATURE_MISSING"
        assert str(e.value) == "missing security envelope"

    def test_envelope_not_dict_code(self):
        with pytest.raises(SignatureError) as e:
            verify_envelope({"security": "nope"}, _resolver())
        assert e.value.code == "SIGNATURE_MISSING"

    def test_bad_alg_code(self):
        with pytest.raises(SignatureError) as e:
            verify_envelope({"security": {"alg": "v2"}}, _resolver())
        assert e.value.code == "SIGNATURE_ALG"
        assert str(e.value) == "envelope alg not allowed"

    def test_missing_key_id_code(self):
        with pytest.raises(SignatureError) as e:
            verify_envelope({"security": {"alg": "v1"}}, _resolver())
        assert e.value.code == "SIGNATURE_MALFORMED"
        assert str(e.value) == "missing key id"

    def test_unknown_key_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id="other")
        with pytest.raises(SignatureError) as e:
            verify_envelope(env, _resolver())
        assert e.value.code == "SIGNATURE_UNKNOWN_KEY"
        assert str(e.value) == "unknown key id"

    def test_stale_timestamp_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID, now=1000)
        with pytest.raises(SignatureError) as e:
            verify_envelope(env, _resolver(), now=2000)  # 1000s > 300s skew
        assert e.value.code == "SIGNATURE_STALE"
        assert str(e.value) == "envelope timestamp stale"

    def test_malformed_timestamp_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["security"]["timestamp"] = "not-a-number"
        with pytest.raises(SignatureError) as e:
            verify_envelope(env, _resolver())
        assert e.value.code == "SIGNATURE_MALFORMED"
        assert str(e.value) == "envelope timestamp malformed"

    def test_payload_digest_mismatch_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["a"] = 2  # tamper
        with pytest.raises(SignatureError) as e:
            verify_envelope(env, _resolver())
        assert e.value.code == "SIGNATURE_BODY"
        assert str(e.value) == "payload digest mismatch"

    def test_signature_mismatch_code(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        env["security"]["signature"] = "0" * 64
        with pytest.raises(SignatureError) as e:
            verify_envelope(env, _resolver())
        assert e.value.code == "SIGNATURE_INVALID"
        assert str(e.value) == "envelope signature mismatch"

    def test_tuple_resolver_accepted(self):
        env = sign_envelope({"a": 1}, SECRET, key_id=KEY_ID)
        res = verify_envelope(env, lambda k: (SECRET, True))
        assert res["key_id"] == KEY_ID
