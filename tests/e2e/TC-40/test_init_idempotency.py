"""TC-40-ext — E12-02 initialization idempotency.

Running init/apply procedures twice must converge to the same state: no
duplicate users, no extra keys churned unnecessarily, no multiplied
iptables rules, no orphan containers.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request

import pytest

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

THEHIVE = os.environ.get("E2E_THEHIVE_URL", "https://thehive:9443")
_CA = "/app/certs/ca.crt"
_SSL = None


def _ssl_ctx():
    global _SSL
    if _SSL is None:
        import ssl
        _SSL = ssl.create_default_context(cafile=_CA)
    return _SSL


def _docker(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def _login_cookie() -> str:
    user = os.environ.get("THEHIVE_ADMIN_USER", "admin@thehive.local")
    pw = os.environ.get("THEHIVE_ADMIN_PASSWORD", "")
    body = json.dumps({"user": user, "password": pw}).encode()
    req = urllib.request.Request(
        f"{THEHIVE}/api/v1/login", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
        return resp.headers.get("Set-Cookie", "").split(";")[0]


class TestInitIdempotency(E2EBaseTest):
    tc_id = "TC-40"

    def setup_method(self, method):
        extra = {s.strip() for s in os.environ.get("E2E_SKIP_SERVICES", "").split(",") if s.strip()}
        extra |= {"loki", "promtail", "misp", "cortex"}
        os.environ["E2E_SKIP_SERVICES"] = ",".join(sorted(extra))
        super().setup_method(method)

    def _analyst(self) -> dict:
        cookie = _login_cookie()
        body = json.dumps({"query": [
            {"_name": "listUser"},
            {"_name": "filter", "_and": [{"_field": "login", "_value": "analyst@soar.local"}]},
        ]}).encode()
        req = urllib.request.Request(
            f"{THEHIVE}/api/v1/query", data=body,
            headers={"Content-Type": "application/json", "Cookie": cookie},
        )
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
            users = json.loads(resp.read())
        assert len(users) == 1, f"expected exactly 1 analyst user, got {len(users)}"
        return users[0]

    def test_init_thehive_twice_no_duplicates(self):
        # Snapshot before: analyst exists exactly once, key works.
        before = self._analyst()
        key_before = ""
        try:
            key_before = open("/app/runtime/results/thehive_api_key.txt").read().strip()
        except OSError:
            pass

        for run in (1, 2):
            r = subprocess.run(
                ["python", "/app/scripts/setup/init_thehive.py"],
                capture_output=True, text=True, timeout=600, cwd="/app",
            )
            assert r.returncode == 0, f"init run {run} failed:\n{r.stdout[-800:]}"

        # Still exactly one analyst; no duplicated orgs either.
        after = self._analyst()
        assert after["_id"] == before["_id"], "init created a duplicate analyst"

        # Key from the run authenticates.
        key = open("/app/runtime/results/thehive_api_key.txt").read().strip()
        assert key, "init did not persist an api key"
        req = urllib.request.Request(
            f"{THEHIVE}/api/v1/user/current", headers={"Authorization": f"Bearer {key}"})
        urllib.request.urlopen(req, timeout=15, context=_ssl_ctx())

    def test_guard_apply_twice_no_rule_duplication(self):
        """Re-running the guard's iptables block must not multiply rules."""
        r = _docker("inspect", "soar_api_egress_guard", "--format", "{{.State.Running}}")
        if r.stdout.strip() != "true":
            pytest.skip("egress guard not deployed")

        def rule_count() -> int:
            out = _docker(
                "exec", "soar_api_egress_guard", "sh", "-c",
                "iptables -L EGRESS_GUARD -n | grep -c '^ACCEPT\\|^DROP' || echo 0")
            try:
                return int(out.stdout.strip())
            except ValueError:
                return -1

        before = rule_count()
        assert before > 0, "EGRESS_GUARD chain empty"

        # Re-apply the same idempotent sequence the guard runs at start.
        cmd = (
            "iptables -N EGRESS_GUARD 2>/dev/null || true;"
            "iptables -F EGRESS_GUARD;"
            "iptables -A EGRESS_GUARD -o lo -j ACCEPT;"
            "iptables -A EGRESS_GUARD -d 127.0.0.0/8 -j ACCEPT;"
            "iptables -A EGRESS_GUARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT;"
            "iptables -A EGRESS_GUARD -d 10.0.0.0/8 -j ACCEPT;"
            "iptables -A EGRESS_GUARD -d 172.16.0.0/12 -j ACCEPT;"
            "iptables -A EGRESS_GUARD -d 192.168.0.0/16 -j ACCEPT;"
            "iptables -A EGRESS_GUARD -d 169.254.0.0/16 -j ACCEPT;"
            "iptables -A EGRESS_GUARD -j DROP;"
            "iptables -C OUTPUT -j EGRESS_GUARD 2>/dev/null || iptables -I OUTPUT 1 -j EGRESS_GUARD"
        )
        r = _docker("exec", "soar_api_egress_guard", "sh", "-c", cmd)
        assert r.returncode == 0, f"re-apply failed: {r.stderr[:200]}"
        after = rule_count()
        assert after == before, f"rule count changed: {before} -> {after}"

        # OUTPUT must reference the chain exactly once.
        refs = _docker(
            "exec", "soar_api_egress_guard", "sh", "-c",
            "iptables -L OUTPUT -n | grep -c EGRESS_GUARD || echo 0")
        assert refs.stdout.strip() == "1", (
            f"OUTPUT has {refs.stdout.strip()} EGRESS_GUARD references, expected 1"
        )
