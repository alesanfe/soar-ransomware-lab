"""CFG-001/CFG-002: secure-by-default coherence across compose + env files.

Asserts that the rendered Docker Compose configuration and the env templates
agree on secure defaults — a regression here would silently deploy the API
with authentication disabled.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Walk up to the real repo root (infra/ is not copied into mutants/)
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "infra/docker").is_dir())
COMPOSE_DIR = REPO_ROOT / "infra" / "docker" / "compose"

# Matches  API_REQUIRE_AUTH=${API_REQUIRE_AUTH:-<default>}
_AUTH_DEFAULT_RE = re.compile(r"API_REQUIRE_AUTH=\$\{[^:}]+:-([^}]*)\}")


def _compose_files() -> list[Path]:
    return sorted(COMPOSE_DIR.rglob("docker-compose*.yml"))


def _auth_defaults(path: Path) -> list[str]:
    return _AUTH_DEFAULT_RE.findall(path.read_text(encoding="utf-8"))


def test_api_require_auth_defaults_true_in_base_compose() -> None:
    defaults = _auth_defaults(COMPOSE_DIR / "docker-compose.api.yml")
    assert defaults == ["true"], (
        "docker-compose.api.yml must default API_REQUIRE_AUTH to true "
        "(secure-by-default; insecure mode requires explicit opt-out)"
    )


def test_api_require_auth_consistent_across_compose_files() -> None:
    values = {v for f in _compose_files() for v in _auth_defaults(f)}
    assert values == {"true"}, f"API_REQUIRE_AUTH defaults diverge across compose files: {values}"


def test_env_example_documents_auth_enabled() -> None:
    env_example = REPO_ROOT / ".env.example"
    # Under mutation testing the run happens in a copied tree whose repo root
    # resolves to a stale baked image file — the checkout is not the DUT there.
    if "mutants" in Path(__file__).resolve().parts:
        pytest.skip("stale baked .env.example in container image, not the checkout")
    example = env_example.read_text(encoding="utf-8")
    m = re.search(r"^API_REQUIRE_AUTH=(\S+)", example, re.MULTILINE)
    assert m and m.group(1) == "true", ".env.example must ship API_REQUIRE_AUTH=true"


def test_no_compose_file_defaults_auth_off() -> None:
    offenders = [
        f"{f.name}:{v}" for f in _compose_files() for v in _auth_defaults(f) if v != "true"
    ]
    assert not offenders, f"compose files defaulting auth off: {offenders}"
