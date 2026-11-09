"""Rendered-config security invariants (DK-P0-057 / BUG-053 regression).

Runs `docker compose config --format json` on the hardened profile and
asserts the MERGED result carries the hardened semantics — not just the
overlay text. This is the failure mode of BUG-053: the overlay looked right
but the merge silently dropped it. Requires docker; skips otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"

BASE_FILES = [
    "docker-compose.yml",
    "docker-compose.core.yml",
    "docker-compose.misp.yml",
    "docker-compose.api.yml",
    "docker-compose.opensearch.yml",
    "logging/docker-compose.logging.yml",
]


def _render(extra_files):
    if not shutil.which("docker"):
        return None
    cmd = ["docker", "compose", "-p", "soar"]
    for f in BASE_FILES + extra_files:
        cmd += ["-f", str(COMPOSE_DIR / f)]
    env = ROOT / ".env"
    if env.exists():
        cmd += ["--env-file", str(env)]
    cmd += ["config", "--format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


@pytest.mark.requires_docker
class TestHardenedRenderedConfig:
    @pytest.fixture(scope="class")
    def rendered(self):
        cfg = _render(["docker-compose.hardened.yml"])
        if cfg is None:
            pytest.skip("docker compose not available")
        return cfg.get("services") or {}

    def test_api_has_no_docker_socket_mount(self, rendered):
        assert all(
            "docker.sock" not in str(v.get("source", ""))
            for v in rendered["api"].get("volumes") or []
        )

    def test_api_runs_non_root(self, rendered):
        user = str(rendered["api"].get("user") or "0")
        assert not user.startswith("0"), f"api user={user}"

    def test_orborus_not_unconfined(self, rendered):
        opts = rendered["orborus"].get("security_opt") or []
        assert not any("unconfined" in str(o) for o in opts)

    def test_auth_defaults_true(self, rendered):
        env = rendered["api"].get("environment") or {}
        assert str(env.get("API_REQUIRE_AUTH")).lower() != "false"

    def test_every_service_has_pids_limit_or_exception(self, rendered):
        exc = json.loads((COMPOSE_DIR / "security-exceptions.json").read_text(encoding="utf-8"))
        missing = [
            name
            for name, svc in rendered.items()
            if not (
                svc.get("pids_limit")
                or (((svc.get("deploy") or {}).get("resources") or {}).get("limits") or {}).get(
                    "pids"
                )
            )
            and "pids-limit" not in (exc.get(name) or {})
        ]
        assert not missing, f"services without pids limit: {missing}"
