#!/usr/bin/env python3
"""TC-11/17 ext: watcher precision matrix + zero-trust verdicts.

Ground truth is ``docker network inspect soar_net`` — the watcher's
/api/connections view must agree exactly (FP=0, FN=0), detect ephemeral
joins with bounded latency, never duplicate after restart, and REJECT a
``worker-*`` impostor whose image is outside WATCHER_MANAGED_IMAGES.
"""

import ipaddress
import json
import subprocess
import time
import uuid

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

NW = "http://network-watcher:8080"
NET = "soar_net"


def _truth() -> dict[str, str]:
    out = subprocess.run(
        ["docker", "network", "inspect", NET, "--format", "{{json .Containers}}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0, out.stderr
    return {
        v["Name"]: v["IPv4Address"].split("/")[0]
        for v in json.loads(out.stdout).values()
    }


def _watched() -> dict[str, str]:
    r = requests.get(f"{NW}/api/connections", timeout=15)
    r.raise_for_status()
    return {c["name"]: c["ip"] for c in r.json()["connections"]}


def _run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker"] + args, capture_output=True, text=True, timeout=timeout)


@pytest.mark.e2e
class TestWatcherPrecision(E2EBaseTest):
    tc_id = "TC-11"

    def setup_method(self, method):
        os_skip = "loki"  # watcher tests do not need the log backend gate
        import os
        os.environ["E2E_SKIP_SERVICES"] = os_skip
        super().setup_method(method)

    def test_precision_tp_fp_fn_matrix(self):
        """Watcher view == daemon ground truth: TP all, FP 0, FN 0, IPs agree."""
        truth = _truth()
        watched = _watched()
        tp = set(watched) & set(truth)
        fp = sorted(set(watched) - set(truth))
        fn = sorted(set(truth) - set(watched))
        self._log(f"precision: TP={len(tp)} FP={fp} FN={fn}")
        assert not fp, f"watcher reports containers not on {NET}: {fp}"
        assert not fn, f"watcher misses containers on {NET}: {fn}"
        mismatched = {n: (watched[n], truth[n]) for n in tp if watched[n] != truth[n]}
        assert not mismatched, f"IP drift watcher-vs-truth: {mismatched}"

    def test_brief_connection_tracked_and_removed(self):
        """An ephemeral container on soar_net appears with bounded latency
        and disappears after death — no ghost entries."""
        name = f"e2e-brief-{uuid.uuid4().hex[:8]}"
        try:
            r = _run(["run", "-d", "--name", name, "--network", NET,
                      "nicolaka/netshoot", "sleep", "300"])
            assert r.returncode == 0, r.stderr
            t0 = time.time()
            while name not in _watched() and time.time() - t0 < 60:
                time.sleep(2)
            appear_ms = (time.time() - t0) * 1000
            assert name in _watched(), f"{name} never appeared in watcher view"
            self._log(f"detection latency: {appear_ms:.0f}ms")
            _run(["kill", name])
            t1 = time.time()
            while name in _watched() and time.time() - t1 < 90:
                time.sleep(3)
            assert name not in _watched(), "ghost entry: dead container still reported"
        finally:
            _run(["rm", "-f", name])

    def test_reported_ips_are_parseable(self):
        """Every reported endpoint IP parses as IPv4/IPv6 — schema sanity."""
        for name, ip in _watched().items():
            assert ipaddress.ip_address(ip), f"malformed watcher IP for {name}: {ip}"

    def test_impostor_worker_rejected_image_not_in_allowlist(self):
        """A worker-* container with an image outside WATCHER_MANAGED_IMAGES
        must be REJECTED — name-prefix spoof is not enough."""
        name = f"worker-evil-{uuid.uuid4().hex[:8]}"
        try:
            r = _run(["run", "-d", "--name", name, "--network", NET,
                      "nicolaka/netshoot", "sleep", "300"])
            assert r.returncode == 0, r.stderr
            deadline = time.time() + 45
            rejected = False
            while time.time() < deadline and not rejected:
                res = _run(["logs", "--since", "90s", "soar_network_watcher"])
                logs = res.stdout + res.stderr  # watcher logs go to stderr
                rejected = f"REJECTED container {name}" in logs or (
                    name in logs and "REJECT" in logs.upper()
                )
                time.sleep(3)
            assert rejected, (
                f"impostor {name} was not rejected — allowlist ineffective "
                f"(watcher trusted name-prefix alone)"
            )
        finally:
            _run(["rm", "-f", name])

    def test_watcher_restart_no_duplicate_entries(self):
        """After a watcher restart the view must not duplicate entries."""
        before = _watched()
        r = _run(["restart", "soar_network_watcher"], timeout=120)
        assert r.returncode == 0, r.stderr
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                if requests.get(f"{NW}/health", timeout=5).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(3)
        else:
            pytest.fail("watcher did not come back healthy")
        time.sleep(10)  # let it re-sync the network view
        after = _watched()
        names = list(requests.get(f"{NW}/api/connections", timeout=15).json()["connections"])
        seen = [c["name"] for c in names]
        assert len(seen) == len(set(seen)), f"duplicate entries after restart: {seen}"
        # A before-container can legitimately die during the restart window
        # (ephemeral Orborus worker-* churns ~1/min under the load generator).
        # It's only a watcher bug if the daemon still lists it on the network.
        truth = _truth()
        missing = {n for n in set(before) - set(after) if n in truth}
        assert not missing, f"restart lost live tracked containers: {missing}"
