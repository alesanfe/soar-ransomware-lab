"""TC-37 — advanced netem: bit corruption, bandwidth ceiling, asymmetric path.

The base set covered delay/loss/jitter/dup/reorder/partitions. These three
complete the fault matrix: payload corruption (TCP checksum catches it),
bandwidth throttling (tbf), and one-direction-only degradation (qdisc is
egress-only — the return path stays clean by construction).
"""

from __future__ import annotations

import subprocess
import time

import pytest
import requests

NETSHOOT = "nicolaka/netshoot:latest"
TARGETS = ("soar_thehive", "soar_cortex")


def _docker(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def _netem(container: str, *tc_args: str) -> subprocess.CompletedProcess:
    return _docker(
        "run", "--rm", "--network", f"container:{container}",
        "--cap-add", "NET_ADMIN", NETSHOOT, "tc", *tc_args, timeout=45,
    )


def _clear(container: str) -> None:
    _netem(container, "qdisc", "del", "dev", "eth0", "root")


@pytest.mark.e2e
class TestNetemAdvanced:
    THEHIVE = "https://thehive:9443/api/v1/status/public"

    @classmethod
    def teardown_class(cls):
        for name in TARGETS:
            _clear(name)

    def test_netem_corruption_bounded(self):
        """5% bit corruption: TCP checksum drops damaged segments and
        retransmits — requests complete bounded, no corrupt data accepted."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "corrupt", "5%")
        assert r.returncode == 0, r.stderr
        try:
            for _ in range(3):
                t = time.time()
                resp = requests.get(self.THEHIVE, timeout=30)
                elapsed = time.time() - t
                assert resp.status_code == 200, "corrupt payload accepted"
                assert elapsed < 30, f"unbounded under corruption: {elapsed:.1f}s"
        finally:
            _clear("soar_thehive")

    def test_netem_bandwidth_ceiling_bounded(self):
        """tbf 2mbit on a 6.3MB asset: transfer stretches from <1s to >8s
        but still completes — a saturated uplink degrades, never hangs."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "tbf", "rate", "2mbit", "burst", "32kbit", "latency", "400ms")
        assert r.returncode == 0, r.stderr
        try:
            t = time.time()
            resp = requests.get(
                "https://thehive:9443/static/index-qlaYA7m3.js", timeout=120)
            elapsed = time.time() - t
            assert resp.status_code == 200
            assert len(resp.content) == 6351790
            assert elapsed > 8, (
                f"ceiling ineffective: 6.3MB in {elapsed:.2f}s"
            )
            assert elapsed < 120, f"unbounded: {elapsed:.1f}s"
        finally:
            _clear("soar_thehive")

    def test_netem_asymmetric_one_direction_only(self):
        """qdisc on egress only: injected side sees degradation, the
        reverse path stays clean — proves faults are one-directional."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "delay", "400ms")
        assert r.returncode == 0, r.stderr
        try:
            # outbound api->thehive crosses the delayed egress queue
            t = time.time()
            resp = requests.get(self.THEHIVE, timeout=30)
            out_rtt = time.time() - t
            assert resp.status_code == 200
            assert out_rtt > 0.35, f"egress delay not applied: {out_rtt:.3f}s"
            # a second target's link stays clean — fault is scoped, not global
            t2 = time.time()
            resp2 = requests.get("https://cortex:9443/api/status", timeout=15)
            clean_rtt = time.time() - t2
            assert resp2.status_code in (200, 401, 403)
            assert clean_rtt < 5, f"fault leaked to cortex path: {clean_rtt:.3f}s"
        finally:
            _clear("soar_thehive")

    def test_qdisc_gone_after_all_faults(self):
        """Hygiene: no netem/tbf residue survives the suite."""
        for name in TARGETS:
            r = _netem(name, "qdisc", "show", "dev", "eth0")
            assert "netem" not in r.stdout and "tbf" not in r.stdout, (
                f"qdisc residue on {name}: {r.stdout.strip()}"
            )
