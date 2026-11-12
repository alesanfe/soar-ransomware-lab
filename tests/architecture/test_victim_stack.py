"""Architecture gates for the victim container (docker-compose.victim.yml).

Static checks over the compose source so a regression in the allowlisted
lab victim fails CI. The victim is the containment-drill target — it must
stay containable (soar.victim label) AND hardened (it runs untrusted-ish
technique simulations).
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "infra/docker/compose/docker-compose.victim.yml"


class _Loader(yaml.SafeLoader):
    """Tolerate compose-spec tags (!reset / !override)."""


_Loader.add_multi_constructor(
    "!",
    lambda loader, suffix, node: (
        loader.construct_sequence(node)
        if suffix == "override" and isinstance(node, yaml.SequenceNode)
        else loader.construct_mapping(node)
        if suffix == "override" and isinstance(node, yaml.MappingNode)
        else None
    ),
)


def _svc() -> dict:
    return yaml.load(COMPOSE.read_text(encoding="utf-8"), Loader=_Loader)["services"]["victim-sim"]


def test_victim_label_present() -> None:
    """Containment allowlist depends on soar.victim=true."""
    svc = _svc()
    assert svc["labels"]["soar.victim"] == "true"
    assert svc["container_name"] == "victim_sim"  # SOAR_CONTAIN_ALLOW_PREFIX


def test_victim_runs_non_root() -> None:
    """VICTIM-EVAL-001: nobody — techniques need no privileges."""
    assert _svc()["user"] == "65534:65534"


def test_victim_full_hardering() -> None:
    svc = _svc()
    assert svc["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in svc["security_opt"]
    assert svc["read_only"] is True
    assert svc["tmpfs"], "techniques need a writable /tmp tmpfs"


def test_victim_restart_policy() -> None:
    """VICTIM-EVAL-002."""
    assert _svc()["restart"] == "unless-stopped"


def test_victim_pids_bound() -> None:
    """VICTIM-EVAL-003: pids bound — a technique fork-bomb can't starve
    the daemon."""
    pids = _svc()["deploy"]["resources"]["limits"]["pids"]
    assert isinstance(pids, int) and 0 < pids <= 64


def test_victim_mem_cpu_bounded() -> None:
    limits = _svc()["deploy"]["resources"]["limits"]
    assert limits["memory"] == "256M"
    assert limits["cpus"] == "0.5"


def test_healthcheck_checks_supervisor() -> None:
    """VICTIM-EVAL-004: the healthcheck must verify PID 1 is the sleep
    supervisor, not merely that python executes."""
    hc = " ".join(_svc()["healthcheck"]["test"])
    assert "/proc/1/comm" in hc
    assert "sleep" in hc


def test_victim_no_host_ports() -> None:
    assert "ports" not in _svc()


def test_log_rotation_configured() -> None:
    """VICTIM-EVAL-005: atomic telemetry streams to stdout — unbounded
    json-file logs fill the disk."""
    logging = _svc()["logging"]
    assert logging["driver"] == "json-file"
    assert logging["options"]["max-size"] == "10m"
    assert logging["options"]["max-file"] == "3"


def test_victim_isolated_to_soar_net() -> None:
    """The victim is a blast-radius target — it must not sit on ti_net or
    other planes it doesn't need."""
    assert _svc()["networks"] == ["soar_net"]


def test_tmpfs_allows_unprivileged_writes() -> None:
    """mode=1777 keeps /tmp writable for user nobody."""
    tmpfs = _svc()["tmpfs"]
    assert any("1777" in str(t) for t in tmpfs)


def test_image_pinned_not_latest() -> None:
    image = _svc()["image"]
    assert "python:3.11-slim" in image
    assert ":latest" not in image
"""Architecture gates — victim simulator (MITRE ATT&CK / CALDERA / Atomic Red Team)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATOMIC = (ROOT / "scripts" / "maintenance" / "run_atomic.py").read_text(encoding="utf-8")


class TestTelemetryPath:
    """Telemetry must reach the log driver — /proc/1/fd/1, not exec stdout."""

    def test_sink_is_pid1_stdout(self):
        assert 'SINK = "/proc/1/fd/1"' in ATOMIC
        assert ">> {SINK}" in ATOMIC or ">> /proc/1/fd/1" in ATOMIC


class TestTtpCoverage:
    """Ransomware kill-chain — every relevant tactic covered."""

    EXPECTED_TACTICS = {
        "execution", "discovery", "persistence", "defense-evasion",
        "credential-access", "collection", "command-and-control", "impact",
    }

    def test_all_ransomware_tactics_covered(self):
        found = set(re.findall(r'Technique\(\s*"T\d+", "[^"]+", "([a-z-]+)"', ATOMIC))
        assert self.EXPECTED_TACTICS <= found, self.EXPECTED_TACTICS - found

    def test_at_least_ten_techniques(self):
        assert len(set(re.findall(r'"(T\d{4})": Technique', ATOMIC))) >= 10


class TestCalderaProfile:
    """CALDERA-style adversary profile + cleanup abilities."""

    def test_ransomware_profile_is_ordered_kill_chain(self):
        m = re.search(r'"ransomware": \[(.*?)\]', ATOMIC, re.S)
        assert m
        tids = re.findall(r'"(T\d{4})"', m.group(1))
        assert tids[-1] == "T1486", "profile must end at Impact (encryption)"
        assert tids[0].startswith("T10"), "profile must start at Discovery/Recon"

    def test_techniques_have_cleanup(self):
        n_clean = len(re.findall(r"cleanup.*rm -f|\[\"rm -f", ATOMIC))
        assert n_clean >= 3, "artifact-producing techniques need cleanup cmds"
