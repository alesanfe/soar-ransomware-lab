"""TC-40-ext — E4-03 TheHive locked-user regression.

BJE rollbacks can resurrect ``analyst@soar.local`` with ``locked:true``;
every renewed API key then 401s. This test forces the locked state, runs
the init script, and asserts the account is unlocked and the key works —
plus that no secret lands in captured output.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.request

import pytest

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.destructive, pytest.mark.slow]

THEHIVE = os.environ.get("E2E_THEHIVE_URL", "https://thehive:9443")
_CA = "/app/certs/ca.crt"
_SSL = None


def _ssl_ctx():
    global _SSL
    if _SSL is None:
        import ssl
        _SSL = ssl.create_default_context(cafile=_CA)
    return _SSL


# Platform superadmin — NOT THEHIVE_ADMIN_USER (that env is the org analyst).
ADMIN = "admin@thehive.local"
ADMIN_PASS = os.environ.get("THEHIVE_ADMIN_PASSWORD", "")
ANALYST = "analyst@soar.local"
ORG = "soar"
_ADMIN_CREDS: tuple[str, str] | None = None


def _admin_creds() -> tuple[str, str]:
    """Superadmin password is rotated to THEHIVE_ADMIN_PASSWORD on init;
    fresh installs still accept the bootstrap 'secret'."""
    global _ADMIN_CREDS
    if _ADMIN_CREDS:
        return _ADMIN_CREDS
    for pw in [p for p in (ADMIN_PASS, "secret") if p]:
        creds = base64.b64encode(f"{ADMIN}:{pw}".encode()).decode()
        req = urllib.request.Request(
            f"{THEHIVE}/api/v1/user/current",
            headers={"Authorization": f"Basic {creds}"},
        )
        try:
            urllib.request.urlopen(req, timeout=15, context=_ssl_ctx())
            _ADMIN_CREDS = (ADMIN, pw)
            return _ADMIN_CREDS
        except Exception:
            continue
    pytest.skip("no valid superadmin credential (rotated + bootstrap both fail)")


def _basic_auth() -> dict:
    """Basic-auth header for the platform superadmin — the path init_thehive
    uses. Cookie sessions hit CSRF protection on PATCH/POST in TheHive 5."""
    user, pw = _admin_creds()
    creds = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {creds}",
    }


def _query(query: list[dict]) -> list[dict]:
    """Platform-admin query — no X-Organisation (same shape init_thehive uses;
    the superadmin session gets 403 if scoped into an org it does not own)."""
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        f"{THEHIVE}/api/v1/query", data=body, headers=_basic_auth(),
    )
    with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
        return json.loads(resp.read())


def _analyst() -> dict:
    users = _query(
        [
            {"_name": "listUser"},
            {"_name": "filter", "_and": [{"_field": "login", "_value": ANALYST}]},
        ],
    )
    assert users, f"{ANALYST} not found"
    return users[0]


def _patch_user(uid: str, patch: dict) -> dict:
    req = urllib.request.Request(
        f"{THEHIVE}/api/v1/user/{uid}", data=json.dumps(patch).encode(),
        method="PATCH",
        headers=_basic_auth(),
    )
    with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
        return json.loads(resp.read() or b"{}")


def _key_works(key: str) -> bool:
    req = urllib.request.Request(
        f"{THEHIVE}/api/v1/user/current",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        urllib.request.urlopen(req, timeout=15, context=_ssl_ctx())
        return True
    except Exception:
        return False


class TestTheHiveLockedRegression(E2EBaseTest):
    tc_id = "TC-40"

    def setup_method(self, method):
        extra = {s.strip() for s in os.environ.get("E2E_SKIP_SERVICES", "").split(",") if s.strip()}
        extra |= {"loki", "promtail", "misp", "cortex"}
        os.environ["E2E_SKIP_SERVICES"] = ",".join(sorted(extra))
        super().setup_method(method)
        try:
            self._user = _analyst()
        except Exception as e:
            pytest.skip(f"admin auth unavailable: {e}")
        self._orig_locked = self._user.get("locked", False)

    def teardown_method(self, method):
        # Restore the original lock state no matter what happened.
        try:
            if hasattr(self, "_user"):
                _patch_user(self._user["_id"], {"locked": self._orig_locked})
        except Exception:
            pass
        super().teardown_method(method)

    def test_init_unlocks_locked_analyst_and_key_works(self):
        uid = self._user["_id"]

        # 1) force the regression state
        _patch_user(uid, {"locked": True})
        assert _analyst().get("locked") is True

        # 2) run the real init — it must unlock BEFORE renewing the key
        r = subprocess.run(
            ["python", "/app/scripts/setup/init_thehive.py"],
            capture_output=True, text=True, timeout=600,
            cwd="/app",
        )
        output = r.stdout + r.stderr

        # 3) unlocked + key renews to a working credential
        user = _analyst()
        assert user.get("locked") is False, "init_thehive left analyst locked"
        try:
            key = open("/app/runtime/results/thehive_api_key.txt").read().strip()
        except OSError:
            key = os.environ.get("THEHIVE_API_KEY", "")
        assert key and _key_works(key), "renewed key does not authenticate"

        # 4) no secret leaked into process output (E4-03)
        for needle in (key, ADMIN_PASS):
            if needle:
                assert needle not in output, f"secret leaked into init output: {needle[:6]}…"
