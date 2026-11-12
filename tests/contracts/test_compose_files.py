"""Contract: compose files stay mergeable — the hardened overlay validates.

A duplicated security_opt item in the hardened overlay once broke `docker
compose config`, silently dropping the whole overlay on recreation (the api
came back root + raw docker socket). This gate reproduces the compose merge
semantics in pure Python: per-service list fields append across files,
duplicated security_opt items are invalid, and !override replaces.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

REPO = Path("/app")
COMPOSE_DIR = REPO / "infra/docker/compose"
BASE_FILES = [
    "docker-compose.yml",
    "docker-compose.core.yml",
    "docker-compose.misp.yml",
    "docker-compose.api.yml",
    "docker-compose.opensearch.yml",
    "logging/docker-compose.logging.yml",
]
HARDENED = "docker-compose.hardened.yml"


class _Loader(yaml.SafeLoader):
    pass


def _any_tag(loader: yaml.Loader, suffix: str, node):
    """Compose tags (!override, !reset) — record the tag on the value."""
    if isinstance(node, MappingNode):
        return {"__tag__": suffix, "value": loader.construct_mapping(node, deep=True)}
    if isinstance(node, SequenceNode):
        return {"__tag__": suffix, "value": loader.construct_sequence(node, deep=True)}
    if isinstance(node, ScalarNode):
        return {"__tag__": suffix, "value": loader.construct_scalar(node)}
    return None


_Loader.add_multi_constructor("!", _any_tag)


def _load(fname: str) -> dict:
    data = yaml.load(
        (COMPOSE_DIR / fname).read_text(encoding="utf-8"), Loader=_Loader
    )
    return data or {}


def _services(docs: list[dict]) -> dict[str, dict]:
    """Merge service dicts the way compose does: mappings merge, lists append,
    !override replaces."""
    merged: dict[str, dict] = {}
    for doc in docs:
        for name, body in (doc.get("services") or {}).items():
            if not isinstance(body, dict):
                continue
            cur = merged.setdefault(name, {})
            for key, val in body.items():
                if isinstance(val, dict) and val.get("__tag__") in ("override", "reset"):
                    cur[key] = val.get("value")
                elif isinstance(val, list) and isinstance(cur.get(key), list):
                    cur[key] = [*cur[key], *val]
                elif isinstance(val, dict) and isinstance(cur.get(key), dict):
                    cur[key] = {**cur[key], **val}
                else:
                    cur[key] = val
    return merged


@pytest.mark.unit
class TestComposeFiles:
    @pytest.fixture(scope="class")
    def hardened_services(self) -> dict:
        docs = [_load(f) for f in [*BASE_FILES, HARDENED]]
        return _services(docs)

    def test_base_files_parse(self):
        for f in [*BASE_FILES, HARDENED]:
            doc = _load(f)
            assert doc.get("services"), f"{f} has no services"

    def test_no_duplicate_security_opt_after_merge(self, hardened_services):
        """The exact regression that invalidated the hardened overlay."""
        for name, body in hardened_services.items():
            opts = body.get("security_opt") or []
            dups = {o for o in opts if opts.count(o) > 1}
            assert not dups, f"{name}: duplicated security_opt {dups} breaks compose merge"

    def test_api_has_no_raw_sock_mount_after_merge(self, hardened_services):
        vols = hardened_services.get("api", {}).get("volumes") or []
        sock = [v for v in vols if "docker.sock" in str(v)]
        assert not sock, f"api still mounts docker.sock after hardened merge: {sock}"

    def test_egress_guard_present_and_scoped(self, hardened_services):
        guard = hardened_services.get("api-egress-guard", {})
        assert guard, "api-egress-guard missing from hardened overlay"
        assert guard.get("network_mode") == "service:api", (
            "egress guard must share the api network namespace"
        )
        caps = guard.get("cap_add") or []
        assert "NET_ADMIN" in caps

    def test_docker_host_points_at_proxy(self, hardened_services):
        env = hardened_services.get("api", {}).get("environment") or []
        vals = [e for e in env if str(e).startswith("DOCKER_HOST=")]
        assert vals and "docker-socket-proxy" in vals[0], (
            f"api DOCKER_HOST not proxied: {vals}"
        )
