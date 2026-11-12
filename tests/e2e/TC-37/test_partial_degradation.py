#!/usr/bin/env python3
"""TC-37: partial degradation — freeze (docker pause) and CPU throttle.

TC-18/TC-36 cover full outages; a SOC more often hits *slow* dependencies:
requests hang until client timeouts fire. ``docker pause`` freezes a service
so every caller experiences connection-hang (worst partial latency), and
``docker update --cpus`` starves CPU. The pipeline must degrade bounded,
never hang forever.
"""

import subprocess
import time
from datetime import UTC, datetime

import pytest
import requests

from tests.e2e.base import E2EBaseTest
from tests.e2e.helpers.docker_control import wait_for_container

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.resilience,
    pytest.mark.destructive,
    pytest.mark.slow,
]


def _docker(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout
    )


class TestPartialDegradation(E2EBaseTest):
    tc_id = "TC-37"

    FROZEN = ("soar_thehive", "soar_cortex")

    @classmethod
    def teardown_class(cls):
        # pause/unpause leaves no other trace — always thaw.
        for name in ("soar_thehive", "soar_cortex"):
            subprocess.run(["docker", "unpause", name], capture_output=True, timeout=30)
            subprocess.run(
                ["docker", "update", "--cpus", "0", name],
                capture_output=True,
                timeout=30,
            )
        sup = super()
        if hasattr(sup, "teardown_class"):
            sup.teardown_class()

    def teardown_method(self, method):
        for name in self.FROZEN:
            _docker("unpause", name, timeout=30)
            _docker("update", "--cpus", "0", name, timeout=30)
        wait_for_container("soar_thehive", timeout=120)
        super().teardown_method(method)

    # ── TC-37-01 ──────────────────────────────────────────────────────────

    def test_thehive_frozen_bounded_hang(self):
        """Freeze TheHive: the pipeline must degrade within a bounded time —
        the workflow may error on thehive nodes but must not hang forever,
        and the API must stay responsive."""
        r = _docker("pause", "soar_thehive", timeout=30)
        assert r.returncode == 0, f"docker pause failed: {r.stderr}"
        try:
            # API must still answer while TheHive is frozen.
            resp = requests.get("http://api:8000/health", timeout=10)
            assert resp.status_code == 200

            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC37-THF-{int(time.time())}"
            payload["detection_time"] = datetime.now(UTC).isoformat()
            t0 = time.time()
            # Webhook admission itself should not block forever.
            wr = requests.post(self.webhook_url, json=payload, timeout=60)
            self._log(
                f"webhook with frozen TheHive: HTTP {wr.status_code} "
                f"in {time.time() - t0:.1f}s"
            )
            assert time.time() - t0 < 90, "webhook hung unbounded with TheHive frozen"
        finally:
            r = _docker("unpause", "soar_thehive", timeout=30)
            assert r.returncode == 0
            assert wait_for_container("soar_thehive", timeout=180)

        # Recovery: a fresh alert completes end-to-end.
        payload = self.build_alert_payload()
        payload["alert_id"] = f"TC37-THF-REC-{int(time.time())}"
        payload["detection_time"] = datetime.now(UTC).isoformat()
        _, execution = self.submit_alert_and_wait(payload, timeout=600)
        assert execution.get("status") == "FINISHED"

    # ── TC-37-02 ──────────────────────────────────────────────────────────

    def test_cortex_cpu_starved_workflow_survives(self):
        """Throttle Cortex to ~5% CPU: analyzer nodes slow down, the workflow
        must still reach a terminal state (never EXECUTING forever)."""
        r = _docker("update", "--cpus", "0.05", "soar_cortex", timeout=30)
        assert r.returncode == 0, f"docker update failed: {r.stderr}"
        try:
            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC37-CTX-{int(time.time())}"
            payload["detection_time"] = datetime.now(UTC).isoformat()
            _, execution = self.submit_alert_and_wait(payload, timeout=600)
            assert execution.get("status") in (
                "FINISHED",
                "FAILED",
            ), f"non-terminal state under CPU starvation: {execution.get('status')}"
        finally:
            _docker("update", "--cpus", "0", "soar_cortex", timeout=30)
            wait_for_container("soar_cortex", timeout=120)


NETSHOOT = "nicolaka/netshoot:latest"
NETEM_TARGETS = ("soar_thehive", "soar_cortex")


def _netem(container: str, *tc_args: str, timeout: int = 45) -> subprocess.CompletedProcess:
    """Apply a tc/netem rule inside the target's netns via a NET_ADMIN
    netshoot sidecar — real kernel-level traffic control, not a mock."""
    return _docker(
        "run", "--rm", "--network", f"container:{container}",
        "--cap-add", "NET_ADMIN", NETSHOOT, "tc", *tc_args, timeout=timeout,
    )


def _qdisc(container: str) -> str:
    r = _docker(
        "run", "--rm", "--network", f"container:{container}",
        "--cap-add", "NET_ADMIN", NETSHOOT, "tc", "qdisc", "show", "dev", "eth0",
        timeout=45,
    )
    return r.stdout


def _clear_netem(container: str) -> None:
    _docker(
        "run", "--rm", "--network", f"container:{container}",
        "--cap-add", "NET_ADMIN", NETSHOOT,
        "tc", "qdisc", "del", "dev", "eth0", "root",
        timeout=45,
    )


class TestNetemDegradation(E2EBaseTest):
    """TC-37-03..07: real tc/netem fault injection — delay, loss, jitter and
    partition. The pipeline must degrade bounded, never hang forever, and the
    qdisc must always be removed on teardown (RES-004)."""

    tc_id = "TC-37"

    THEHIVE = "https://thehive:9443/api/v1/status/public"

    @classmethod
    def teardown_class(cls):
        # An orphan qdisc would silently degrade every later test.
        for name in NETEM_TARGETS:
            _clear_netem(name)

    def _rtt(self, timeout: float = 15) -> tuple[float, int]:
        t = time.time()
        r = requests.get(self.THEHIVE, timeout=timeout)
        return time.time() - t, r.status_code

    def test_netem_delay_250ms_bounded(self):
        """250ms delay on TheHive's link: requests slow but complete, no
        error, no unbounded stall."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "delay", "250ms")
        assert r.returncode == 0, r.stderr
        try:
            rtt, code = self._rtt()
            assert code == 200
            assert rtt > 0.3, f"netem not applied? rtt={rtt:.3f}"
            assert rtt < 15, f"unbounded: rtt={rtt:.3f}"
        finally:
            _clear_netem("soar_thehive")

    def test_netem_packet_loss_10pct_bounded(self):
        """10% loss: TCP retransmits must carry the requests through — every
        call completes inside the bound, none hangs forever."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "loss", "10%")
        assert r.returncode == 0, r.stderr
        try:
            for _ in range(4):
                rtt, code = self._rtt(timeout=30)
                assert code == 200, f"request failed under 10% loss: {code}"
                assert rtt < 30, f"unbounded under loss: {rtt:.3f}"
        finally:
            _clear_netem("soar_thehive")

    def test_netem_jitter_delay_bounded(self):
        """150ms ± 75ms jitter: variable latency must still complete."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "delay", "150ms", "75ms")
        assert r.returncode == 0, r.stderr
        try:
            for _ in range(3):
                rtt, code = self._rtt(timeout=20)
                assert code == 200
                assert rtt < 20
        finally:
            _clear_netem("soar_thehive")

    def test_netem_partition_fails_bounded_then_recovers(self):
        """100% loss = unilateral partition: the client fails BOUNDED (socket
        cap + request timeout), and service returns after the qdisc is
        removed — no zombie connection state."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "loss", "100%")
        assert r.returncode == 0, r.stderr
        try:
            t = time.time()
            with pytest.raises(requests.RequestException):
                requests.get(self.THEHIVE, timeout=15)
            assert time.time() - t < 60, "partition produced an unbounded hang"
        finally:
            _clear_netem("soar_thehive")
        # Recovery: connectivity is restored the instant netem is removed.
        deadline = time.time() + 60
        code = 0
        while time.time() < deadline:
            try:
                r = requests.get(self.THEHIVE, timeout=10)
                code = r.status_code
                if code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        assert code == 200, f"TheHive did not recover after partition: {code}"

    def test_no_orphan_qdisc_after_degradation(self):
        """Teardown hygiene: no netem rule may survive the suite — an orphan
        qdisc would poison every subsequent test run."""
        qdisc = _qdisc("soar_thehive")
        assert "netem" not in qdisc, f"orphan qdisc on thehive: {qdisc}"


class TestNetemAdvanced(E2EBaseTest):
    """TC-37-08..10: duplication, reordering and a real unilateral partition
    (egress-only iptables DROP inside the target netns)."""

    tc_id = "TC-37"
    THEHIVE = TestNetemDegradation.THEHIVE

    @classmethod
    def teardown_class(cls):
        for name in NETEM_TARGETS:
            _clear_netem(name)
            _docker(
                "run", "--rm", "--network", f"container:{name}",
                "--cap-add", "NET_ADMIN", NETSHOOT,
                "iptables", "-F", "OUTPUT", timeout=45,
            )

    def _rtt(self, timeout: float = 20):
        t = time.time()
        r = requests.get(self.THEHIVE, timeout=timeout)
        return time.time() - t, r.status_code

    def test_netem_duplication_bounded(self):
        """25% packet duplication: TCP dedupes, every request completes."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "duplicate", "25%")
        assert r.returncode == 0, r.stderr
        try:
            for _ in range(3):
                rtt, code = self._rtt()
                assert code == 200, f"failed under duplication: {code}"
                assert rtt < 20
        finally:
            _clear_netem("soar_thehive")

    def test_netem_reorder_bounded(self):
        """Reordering (delay gap + reorder probability): out-of-order
        segments must still reassemble into valid responses."""
        r = _netem("soar_thehive", "qdisc", "add", "dev", "eth0",
                   "root", "netem", "delay", "50ms", "reorder", "50%", "50%")
        assert r.returncode == 0, r.stderr
        try:
            for _ in range(3):
                rtt, code = self._rtt()
                assert code == 200, f"failed under reordering: {code}"
                assert rtt < 20
        finally:
            _clear_netem("soar_thehive")

    def test_unilateral_partition_egress_drop(self):
        """One-way partition: iptables OUTPUT DROP inside TheHive's netns —
        inbound packets arrive, replies never leave. The client must fail
        bounded and recover the instant the rule is flushed."""
        add = _docker(
            "run", "--rm", "--network", "container:soar_thehive",
            "--cap-add", "NET_ADMIN", NETSHOOT,
            "iptables", "-A", "OUTPUT", "-p", "tcp", "--sport", "9443",
            "-j", "DROP", timeout=45,
        )
        assert add.returncode == 0, add.stderr
        try:
            t = time.time()
            with pytest.raises(requests.RequestException):
                requests.get(self.THEHIVE, timeout=15)
            assert time.time() - t < 60
        finally:
            _docker(
                "run", "--rm", "--network", "container:soar_thehive",
                "--cap-add", "NET_ADMIN", NETSHOOT,
                "iptables", "-D", "OUTPUT", "-p", "tcp", "--sport", "9443",
                "-j", "DROP", timeout=45,
            )
        deadline = time.time() + 60
        code = 0
        while time.time() < deadline:
            try:
                r = requests.get(self.THEHIVE, timeout=10)
                code = r.status_code
                if code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        assert code == 200, "no recovery after unilateral partition"
