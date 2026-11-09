#!/usr/bin/env python3
"""Architecture test: docker socket exposure allowlist (VAL-014).

Parses every compose file and fails if a service mounts the docker
socket without being on the justified-access allowlist. This is the
regression guard required by VAL-014's acceptance criteria.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"

# Services allowed to mount the docker socket, with justification:
# - api: container health checks + enforced containment (VAL-010)
# - orborus: spawns Shuffle worker containers (core function)
# - network-watcher: monitors container network events
# - promtail: docker_sd_configs log discovery (read-only use)
# - cortex: DinD analyzers (live: via Docker Desktop proxy path)
# - shuffle-backend: app lifecycle management; live mount resolves to
#   Docker Desktop's docker.proxy.sock, not the raw socket
# - docker-socket-proxy: IS the hardened proxy (mounts raw socket by
#   design; exposes limited API verbs to the rest)
JUSTIFIED = {
    "api",
    "orborus",
    "network-watcher",
    "network_watcher",
    "promtail",
    "cortex",
    "shuffle-backend",
    "shuffle_backend",
    "docker-socket-proxy",
}

SOCKET_MARKERS = ("docker.sock", "docker.proxy.sock", "docker-socket-proxy")

# Services that only OBSERVE the docker API must mount the socket read-only.
# network-watcher only reads container/network events; promtail only reads
# container metadata for log discovery. A writable mount would let either
# one create/pause/kill containers — privilege they do not need.
READONLY_REQUIRED = {"network-watcher", "network_watcher", "promtail"}


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader tolerant of compose-spec tags (!reset, !override)."""


def _compose_tag(loader, suffix, node):
    """Mirror Compose v5 semantics: !reset discards its node (resets to
    null/empty), !override replaces the merged value with the tagged node."""
    if suffix == "override":
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return loader.construct_scalar(node)
    return None


_ComposeLoader.add_multi_constructor("!", _compose_tag)


def _compose_files() -> list[Path]:
    return sorted(COMPOSE_DIR.glob("docker-compose*.yml")) + sorted(
        (COMPOSE_DIR / "logging").glob("*.yml")
    )


def _socket_mounts() -> dict[str, list[str]]:
    """Map service -> compose files where it mounts a docker socket."""
    hits: dict[str, list[str]] = {}
    for f in _compose_files():
        data = yaml.load(f.read_text(encoding="utf-8"), Loader=_ComposeLoader) or {}
        for name, svc in (data.get("services") or {}).items():
            for vol in svc.get("volumes", []) or []:
                vol_str = vol if isinstance(vol, str) else str(vol.get("source", ""))
                if any(m in vol_str for m in SOCKET_MARKERS):
                    hits.setdefault(name, []).append(f.name)
    return hits


class TestDockerSocketAllowlist:
    def test_no_unauthorized_socket_mounts(self):
        unauthorized = {
            svc: files for svc, files in _socket_mounts().items() if svc not in JUSTIFIED
        }
        assert not unauthorized, (
            "services mounting docker socket without justification: "
            f"{unauthorized}. Add justification to docs or remove the mount."
        )

    def test_compose_files_parse(self):
        assert _compose_files(), "no compose files found — check COMPOSE_DIR"

    def test_shuffle_backend_uses_proxy_not_raw(self):
        """Live check: shuffle-backend's socket mount resolves to a filtered
        socket, never the raw daemon socket.

        On Docker Desktop the VM's /var/run/docker.sock IS already the
        filtered docker.proxy.sock (containers cannot reach the real host
        daemon), so it is acceptable there. On native Linux
        /var/run/docker.sock is the raw daemon socket — the mount must
        instead resolve to docker.proxy.sock (or the docker-socket-proxy
        hardened service). Skips when the stack is not running."""
        docker = pytest.importorskip("docker")
        try:
            client = docker.from_env()
            container = client.containers.get("soar_shuffle_backend")
            server_name = str(client.info().get("Name", ""))
        except Exception:
            pytest.skip("soar_shuffle_backend not running")
        sources = [m["Source"] for m in container.attrs.get("Mounts", [])]
        sock_mounts = [s for s in sources if "sock" in s.lower()]
        assert sock_mounts, "expected a socket mount on shuffle-backend"
        is_desktop = "desktop" in server_name.lower()
        if is_desktop:
            # Docker Desktop: the VM socket bind source is already the
            # filtered proxy — raw-daemon exposure is impossible here.
            assert any(
                s in ("/var/run/docker.sock",) or "docker.proxy.sock" in s for s in sock_mounts
            )
        else:
            assert not any(s == "/var/run/docker.sock" for s in sock_mounts), (
                "raw daemon socket mounted on native Linux — route through "
                "docker-socket-proxy or docker.proxy.sock"
            )
            assert any("docker.proxy.sock" in s or "proxy" in s for s in sock_mounts)

    def test_known_inventory_matches(self):
        """Documented live inventory: raw socket on api, orborus,
        network-watcher, promtail; proxy on cortex + shuffle-backend."""
        found = set(_socket_mounts())
        unexpected = found - JUSTIFIED
        assert not unexpected
        for expected in ("api", "orborus", "promtail"):
            assert expected in found

    def test_readonly_consumers_mount_socket_ro(self):
        """Observe-only services must never get a writable docker socket."""
        violations: dict[str, list[str]] = {}
        for f in _compose_files():
            data = yaml.load(f.read_text(encoding="utf-8"), Loader=_ComposeLoader) or {}
            for name, svc in (data.get("services") or {}).items():
                if name not in READONLY_REQUIRED:
                    continue
                for vol in svc.get("volumes", []) or []:
                    vol_str = vol if isinstance(vol, str) else str(vol.get("source", ""))
                    if not any(m in vol_str for m in SOCKET_MARKERS):
                        continue
                    # Hardened profile resets volumes to [] via docker-socket-proxy;
                    # a remaining raw-socket mount must be read-only.
                    if not vol_str.rstrip().endswith(":ro"):
                        violations.setdefault(name, []).append(f"{f.name}: {vol_str}")
        assert not violations, (
            "observe-only services mounting docker socket read-write: "
            f"{violations}. Mount it with :ro."
        )


class TestHardenedApiVolumes:
    """BUG-053: ``volumes: !reset`` followed by a block sequence is
    silently dropped by Docker Compose v5 (the tag resolves to null and
    the entries never merge) — the hardened api then runs the baked
    image code with no bind mounts, so env-gated controls read stale
    defaults. The api block must use ``volumes: !override`` so the
    hardened mount list actually applies."""

    HARDENED = COMPOSE_DIR / "docker-compose.hardened.yml"

    def test_no_dead_reset_entries(self):
        import re

        text = self.HARDENED.read_text(encoding="utf-8")
        dead = re.findall(r"!reset\s*\n\s*-\s", text)
        assert not dead, (
            "hardened compose has `!reset` followed by list entries — "
            "Compose v5 discards them; use `!override` (or `!reset []` for empty)"
        )

    def test_api_volumes_resolve_non_empty(self):
        data = yaml.load(self.HARDENED.read_text(encoding="utf-8"), Loader=_ComposeLoader)
        volumes = (data.get("services") or {}).get("api", {}).get("volumes")
        assert volumes, (
            "hardened api volumes resolved empty — bind mounts lost, "
            "container runs stale baked code"
        )
        assert any("/app/src" in str(v) for v in volumes)
        assert any("/app/scripts" in str(v) for v in volumes)


class TestQualityToolMounts:
    """BUG-058: the api container runs the ``tests/quality`` suite, but
    tool config files living at the repo root were not bind-mounted —
    ``parse_bandit`` invokes ``bandit -c bandit.yaml`` which exited with
    "Could not read config file" inside the container (empty stdout,
    unparsable). Every root-level config file a quality tool reads
    must be mounted on every api compose profile that runs tests."""

    CONFIG_MOUNTS = (".coveragerc", "bandit.yaml", "pytest.ini", "pyproject.toml")
    API_COMPOSE = COMPOSE_DIR / "docker-compose.api.yml"
    HARDENED = COMPOSE_DIR / "docker-compose.hardened.yml"

    @staticmethod
    def _api_volumes(path: Path) -> list[str]:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_ComposeLoader)
        return [
            str(v) for v in (data.get("services") or {}).get("api", {}).get("volumes", []) or []
        ]

    @pytest.mark.parametrize("config", CONFIG_MOUNTS)
    def test_lab_api_mounts_tool_configs(self, config):
        volumes = self._api_volumes(self.API_COMPOSE)
        assert any(f"/app/{config}" in v for v in volumes), (
            f"{config} not mounted in lab api — quality tests that need it "
            "fail inside the container (BUG-058)"
        )

    @pytest.mark.parametrize("config", CONFIG_MOUNTS)
    def test_hardened_api_mounts_tool_configs(self, config):
        volumes = self._api_volumes(self.HARDENED)
        assert any(f"/app/{config}" in v for v in volumes), (
            f"{config} not mounted in hardened api — quality tests that need "
            "it fail inside the container (BUG-058)"
        )
