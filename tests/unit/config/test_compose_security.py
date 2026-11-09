"""Regression tests for compose-level security invariants (DK-P0-002/004/057).

Two layers:
- Static: the compose source files must keep the hardened-only semantics
  (!override on list fields, secure defaults) — runs everywhere.
- Rendered: `docker compose config` must yield an effective config where the
  security properties survived the merge — this is what BUG-053 violated
  (overlay semantics silently dropped). Requires docker; skips otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

# Walk up to the real repo root (infra/ is not copied into mutants/)
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "infra/docker").is_dir())
COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"
HARDENED = COMPOSE_DIR / "docker-compose.hardened.yml"
VALIDATOR = ROOT / "scripts" / "setup" / "validate_compose_security.py"

BASE_FILES = [
    "docker-compose.yml",
    "docker-compose.core.yml",
    "docker-compose.misp.yml",
    "docker-compose.api.yml",
    "docker-compose.opensearch.yml",
    "logging/docker-compose.logging.yml",
]


def _load_validator():
    spec = importlib.util.spec_from_file_location("vcs", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("vcs", mod)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------- static ------


class TestHardenedSourceSemantics:
    @staticmethod
    def _service_block(text: str, service: str) -> str:
        """Extract a top-level service block (2-space key, ends at the next
        2-space key or EOF). Nested lines are indented deeper, so the split
        anchor must require a non-space right after the two spaces."""
        m = re.search(
            rf"^  {re.escape(service)}:\n(.*?)(?=^  \S|\Z)", text, re.MULTILINE | re.DOTALL
        )
        assert m, f"service {service} not found in hardened overlay"
        return m.group(1)

    def test_orborus_seccomp_list_is_overridden_not_appended(self):
        """BUG-053/DK-P1-013: security_opt is a list — a plain YAML list in the
        overlay APPENDS to the base and leaves seccomp:unconfined in place.
        The orborus block must use !override (or !reset) to replace it."""
        text = HARDENED.read_text(encoding="utf-8")
        orborus_block = "\n".join(
            ln
            for ln in self._service_block(text, "orborus").splitlines()
            if not ln.strip().startswith("#")
        )
        assert "seccomp:unconfined" not in orborus_block
        assert "!override" in orborus_block or "!reset" in orborus_block, (
            "orborus security_opt must replace the base list — appending "
            "silently keeps seccomp:unconfined"
        )

    def test_hardened_requires_auth(self):
        text = HARDENED.read_text(encoding="utf-8")
        assert "API_REQUIRE_AUTH=${API_REQUIRE_AUTH:-true}" in text

    def test_api_non_root_in_hardened(self):
        text = HARDENED.read_text(encoding="utf-8")
        api_block = self._service_block(text, "api")
        assert 'user: "${API_UID:-1000}:${API_GID:-1000}"' in api_block
        assert "cap_drop" in api_block

    def test_no_duplicate_service_keys_in_hardened(self):
        """Duplicate top-level service keys in one file are last-wins, not
        merged — a regression class we already hit once."""
        names = [
            ln.strip().rstrip(":")
            for ln in HARDENED.read_text(encoding="utf-8").splitlines()
            if ln.startswith("  ") and not ln.startswith("   ") and ln.strip().endswith(":")
        ]
        dupes = {n for n in names if names.count(n) > 1}
        assert not dupes, f"duplicate service keys in hardened overlay: {dupes}"

    def test_exceptions_file_has_expiry_and_reason(self):
        exc = json.loads((COMPOSE_DIR / "security-exceptions.json").read_text(encoding="utf-8"))
        for svc, checks in exc.items():
            if svc.startswith("_"):
                continue
            for check_id, entry in checks.items():
                assert entry.get("reason"), f"{svc}/{check_id}: missing reason"
                assert entry.get("expires"), f"{svc}/{check_id}: missing expires"


# ------------------------------------------------------ validator logic ----


class TestValidator:
    def test_privileged_is_critical(self):
        v = _load_validator()
        findings = v.evaluate_service("api", {"privileged": True}, "hardened", {})
        assert any(f["check"] == "no-privileged" and f["severity"] == "CRITICAL" for f in findings)

    def test_seccomp_unconfined_flagged(self):
        v = _load_validator()
        findings = v.evaluate_service(
            "orborus", {"security_opt": ["seccomp:unconfined"]}, "hardened", {}
        )
        assert any(f["check"] == "no-unconfined-seccomp" for f in findings)

    def test_docker_socket_detected_rw_and_ro(self):
        v = _load_validator()
        for ro in (True, False):
            svc = {
                "volumes": [
                    {
                        "source": "/var/run/docker.sock",
                        "target": "/var/run/docker.sock",
                        "read_only": ro,
                    }
                ]
            }
            findings = v.evaluate_service("api", svc, "hardened", {})
            assert any(f["check"] == "no-direct-docker-socket" for f in findings), ro

    def test_auth_disabled_fails_in_hardened(self):
        v = _load_validator()
        svc = {"environment": {"API_REQUIRE_AUTH": "false"}}
        findings = v.evaluate_service("api", svc, "hardened", {})
        f = next(f for f in findings if f["check"] == "auth-enabled")
        assert f["severity"] == "CRITICAL" and not f["excepted"]

    def test_expired_exception_becomes_violation(self):
        v = _load_validator()
        exc = {"api": {"no-privileged": {"reason": "test", "expires": "2000-01-01"}}}
        findings = v.evaluate_service("api", {"privileged": True}, "hardened", exc)
        f = next(f for f in findings if f["check"] == "no-privileged")
        assert not f["excepted"]
        assert "EXPIRED" in (f["note"] or "")

    def test_pids_limit_via_deploy_limits(self):
        v = _load_validator()
        svc = {"deploy": {"resources": {"limits": {"pids": 128}}}}
        findings = v.evaluate_service("api", svc, "hardened", {})
        assert not any(f["check"] == "pids-limit" for f in findings)


# The rendered-config assertions live in
# tests/integration/test_compose_rendered.py (needs `docker compose config`,
# which unit tests must not invoke per tests/unit/conftest.py).
