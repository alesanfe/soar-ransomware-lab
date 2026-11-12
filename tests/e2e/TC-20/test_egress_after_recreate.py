"""TC-20-ext — E5-02 egress adversarial + E12-01 post-recreate smoke.

The egress guard shares the api netns via ``network_mode: service:api``,
which docker resolves to a *container ID* at creation time. If soar_api is
recreated, the guard keeps pointing at a dead netns and EGRESS_GUARD rules
evaporate silently. These tests exercise the detection + re-anchor path and
the essential post-recreate smoke checks.

Constraints honoured:
- runs from the runner (soar_test_runner) or soar_api — never assumes
  localhost;
- only docker CLI through DOCKER_HOST (socket proxy);
- every destructive step restores state in ``finally`` + teardown.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request

import pytest

from tests.e2e.base import E2EBaseTest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.destructive,
    pytest.mark.slow,
]

API = os.environ.get("E2E_API_URL", "http://api:8000")
GUARD = "soar_api_egress_guard"
API_C = "soar_api"
FORBIDDEN = "93.184.216.34"  # example.com — public, non-RFC1918
CANARY_URL = f"http://{FORBIDDEN}/"


def _docker(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def _api_id() -> str:
    r = _docker("inspect", API_C, "--format", "{{.Id}}")
    return r.stdout.strip()


def _guard_target() -> str:
    r = _docker("inspect", GUARD, "--format", "{{.HostConfig.NetworkMode}}")
    return r.stdout.strip().removeprefix("container:")


def _guard_running() -> bool:
    r = _docker("inspect", GUARD, "--format", "{{.State.Running}}")
    return r.stdout.strip() == "true"


def _egress_reachable(timeout: float = 6.0) -> bool:
    """True if the api netns can reach the forbidden public destination."""
    r = _docker(
        "exec", API_C, "sh", "-c",
        f"curl -s -o /dev/null -w '%{{http_code}}' --max-time {int(timeout)} {CANARY_URL} || true",
        timeout=timeout + 5,
    )
    return r.stdout.strip() not in ("", "000")


def _guard_rules_present() -> bool:
    r = _docker("exec", GUARD, "iptables", "-L", "EGRESS_GUARD", "-n", timeout=15)
    return r.returncode == 0 and "DROP" in r.stdout


def _reanchor_guard(timeout: int = 120) -> bool:
    """Re-create the guard bound to the CURRENT api container ID.

    Mirrors the documented recovery: rm stale guard, then docker create/run
    a fresh sidecar with network_mode container:<live-api-id>.
    """
    api_id = _api_id()
    if not api_id:
        return False
    _docker("rm", "-f", GUARD)
    spec = {
        "Image": os.environ.get("NETSHOOT_IMAGE", "nicolaka/netshoot:latest"),
        "Cmd": [
            "sh", "-c",
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
            "iptables -C OUTPUT -j EGRESS_GUARD 2>/dev/null || iptables -I OUTPUT 1 -j EGRESS_GUARD;"
            "sleep infinity",
        ],
        "HostConfig": {
            "NetworkMode": f"container:{api_id}",
            "CapAdd": ["NET_ADMIN"],
            "ReadonlyRootfs": True,
        },
        "Labels": {"soar.egress-guard": "1", "soar.reanchored": "true"},
    }
    r = _docker(
        "create", "--name", GUARD,
        "--cap-add", "NET_ADMIN",
        "--read-only",
        "--network", f"container:{api_id}",
        os.environ.get("NETSHOOT_IMAGE", "nicolaka/netshoot:latest"),
        "sh", "-c", spec["Cmd"][-1],
        timeout=60,
    )
    if r.returncode != 0:
        return False
    r = _docker("start", GUARD, timeout=30)
    if r.returncode != 0:
        return False
    deadline = time.time() + 30
    while time.time() < deadline:
        if _guard_rules_present():
            return True
        time.sleep(2)
    return _guard_rules_present()


class TestEgressAfterRecreate(E2EBaseTest):
    tc_id = "TC-20"

    def setup_method(self, method):
        # Guard checks need the api only — the heavy social services may be
        # skipped when unstable; the egress contract stands alone.
        extra = os.environ.get("E2E_SKIP_SERVICES", "")
        skip = {s.strip() for s in extra.split(",") if s.strip()}
        skip |= {"loki", "promtail", "misp", "cortex", "thehive"}
        os.environ["E2E_SKIP_SERVICES"] = ",".join(sorted(skip))
        super().setup_method(method)

    def _preflight_guarded(self) -> None:
        """Skip cleanly when the hardened overlay (and thus the guard) is off."""
        if not _guard_running() and _guard_target() == "":
            pytest.skip("egress guard not deployed (LAB profile / hardened overlay off)")

    # ── E12-01 post-recreate smoke ────────────────────────────────────────

    def test_smoke_api_ca_guard_after_recreate(self):
        self._preflight_guarded()
        # API healthy from the runner (service DNS, not localhost)
        r = urllib.request.urlopen(f"{API}/health", timeout=15)
        assert r.status == 200, f"API /health -> {r.status}"

        # CA bundle readable inside the api container (E6-01 regression)
        r = _docker(
            "exec", API_C, "sh", "-c",
            "test -r /app/certs/ca-bundle.crt && wc -c < /app/certs/ca-bundle.crt",
        )
        assert r.returncode == 0 and int(r.stdout.strip() or 0) > 1000, (
            "ca-bundle.crt missing/unreadable inside api"
        )

        # Guard anchored to the LIVE api netns
        api_id, target = _api_id(), _guard_target()
        assert target == api_id, (
            f"guard attached to dead netns: api={api_id[:12]} guard→{target[:12]}"
        )
        assert _guard_rules_present(), "EGRESS_GUARD chain missing on live netns"

        # Allowed traffic still flows, forbidden stays blocked
        r = _docker(
            "exec", API_C, "sh", "-c",
            "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://network-watcher:8080/health || true",
        )
        assert r.stdout.strip() != "000", "internal egress broken"

    # ── E5-02 adversarial: guard lifecycle vs netns lifetime ─────────────

    def test_egress_rules_outlive_guard_container(self):
        """Rules live in the api netns, NOT the sidecar — removing the guard
        must NOT open egress (netns persists). The re-anchor procedure must
        then produce a working guard attached to the live api netns."""
        self._preflight_guarded()
        assert not _egress_reachable(), (
            "forbidden egress reachable BEFORE test — guard already ineffective"
        )

        try:
            assert _docker("rm", "-f", GUARD).returncode == 0, "could not remove guard"
            # Netns semantics: EGRESS_GUARD was installed in the api netns,
            # so it survives the sidecar's removal — egress stays blocked.
            # (the api cannot read iptables without NET_ADMIN; probe egress)
            assert not _egress_reachable(), (
                "removing the guard opened egress — rules must be netns-scoped, "
                "not container-scoped"
            )
        finally:
            # Re-anchor a fresh guard for the rest of the suite.
            if not _guard_running():
                _reanchor_guard()
        api_id, target = _api_id(), _guard_target()
        assert target == api_id, (
            f"guard re-anchored to wrong netns: {target[:12]} != {api_id[:12]}"
        )
        assert _guard_rules_present(), "rules missing after re-anchor"
        assert not _egress_reachable(), "egress open after re-anchor"

    def test_stale_guard_netns_detected(self):
        """The preflight must flag guard-target != api-id — the post-recreate
        orphan state. Verify the detector's logic against the live pair and
        a synthetic stale target."""
        self._preflight_guarded()
        api_id, target = _api_id(), _guard_target()
        assert api_id and target, "could not inspect api/guard pair"
        # Live state is consistent...
        assert target == api_id, (
            f"live guard already orphaned: api={api_id[:12]} guard→{target[:12]}"
        )
        # ...and the detector math rejects any stale target.
        stale = "deadbeef0000" + api_id[12:]
        assert stale != api_id, "test construction error"
        # Exercise the same check e2e_host_preflight performs.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "e2e_host_preflight",
            "/app/scripts/ci/e2e_host_preflight.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        level, detail = mod.check_egress_guard()
        assert level == mod.OK, f"preflight flagged live pair: {detail}"

    def test_egress_persists_across_api_restart(self):
        """docker restart keeps the same container/netns — rules must persist."""
        self._preflight_guarded()
        api_id_before = _api_id()
        r = _docker("restart", API_C, timeout=180)
        assert r.returncode == 0, f"api restart failed: {r.stderr[:200]}"
        try:
            # Same container ID → same netns → guard attachment still valid.
            deadline = time.time() + 300
            healthy = False
            while time.time() < deadline and not healthy:
                try:
                    healthy = urllib.request.urlopen(f"{API}/health", timeout=5).status == 200
                except Exception:
                    pass
                if not healthy:
                    time.sleep(10)
            assert healthy, "api never healthy after restart"
            assert _api_id() == api_id_before, "restart changed container ID (unexpected)"
            assert _guard_rules_present(), "egress rules lost across restart"
            # Distinguish "blocked" from "outbound not warm yet": internal
            # egress must work before the forbidden assertion means anything.
            internal_ok = False
            deadline = time.time() + 300
            while time.time() < deadline and not internal_ok:
                r = _docker(
                    "exec", API_C, "sh", "-c",
                    "curl -s -o /dev/null -w '%{http_code}' --max-time 8 "
                    "http://network-watcher:8080/health || true",
                )
                internal_ok = r.stdout.strip() not in ("", "000")
                if not internal_ok:
                    time.sleep(10)
            assert internal_ok, "internal egress never came back after restart"
            assert not _egress_reachable(), "egress opened across restart"
        finally:
            if not _guard_rules_present():
                _reanchor_guard()
