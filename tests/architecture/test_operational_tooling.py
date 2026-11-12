"""Architecture gates — operational tooling (eval 44).

Static invariants for the Makefiles + scripts/ surface documented in
``docs/44-eval-operational-tooling.md``: cross-OS target parity, .PHONY
coverage, no dead script references, no duplicate targets, and the
scripts-manifest freshness gate.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAKEFILES = [ROOT / "Makefile.win", ROOT / "Makefile.linux"]
CI = ROOT / ".github" / "workflows" / "ci.yml"
MANIFEST_SCRIPT = ROOT / "scripts" / "ci" / "generate_scripts_manifest.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _targets(src: str) -> set[str]:
    ts = {m.group(1) for m in re.finditer(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*:(?![=])", src, re.M)}
    ts.discard("PHONY")
    return ts


def _phony(src: str) -> set[str]:
    out = set()
    for m in re.finditer(r"\.PHONY:\s*([^\n]+)", src):
        out.update(m.group(1).split())
    return out


def test_makefile_target_parity_across_os():
    win, lin = (_targets(_read(m)) for m in MAKEFILES)
    assert win == lin, f"Makefile drift — win-only: {win-lin}, linux-only: {lin-win}"


def test_all_targets_declared_phony():
    """OPS-EVAL-001 regression: un-PHONY'd targets break silently on name collisions."""
    for mk in MAKEFILES:
        src = _read(mk)
        missing = _targets(src) - _phony(src)
        assert not missing, f"{mk.name} targets missing .PHONY: {sorted(missing)}"


def test_no_duplicate_target_definitions():
    for mk in MAKEFILES:
        seen: dict[str, int] = {}
        for m in re.finditer(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*:(?![=])", _read(mk), re.M):
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
        dupes = {k: v for k, v in seen.items() if v > 1 and k != "PHONY"}
        assert not dupes, f"{mk.name} duplicated targets: {dupes}"


def test_no_dead_script_references_in_makefiles():
    for mk in MAKEFILES:
        dead = [
            r for r in re.findall(r"scripts/[\w/]+\.py", _read(mk))
            if not (ROOT / r).exists()
        ]
        assert not dead, f"{mk.name} references missing scripts: {dead}"


def test_scripts_manifest_gate_in_ci():
    src = _read(CI)
    assert "generate_scripts_manifest.py --check" in src
    assert MANIFEST_SCRIPT.exists()


def test_no_loose_scripts_in_repo_root():
    """AGENTS.md: no stray _*.py scripts at repo root — canonical home is scripts/."""
    loose = [p.name for p in ROOT.glob("*.py")]
    assert not loose, f"loose scripts at repo root: {loose}"


def test_core_operational_targets_exist():
    body = _read(MAKEFILES[0])
    for t in ("doctor", "preflight", "health", "backup", "restore", "drill-obs",
              "simulate", "clean-shuffle", "reset"):
        assert re.search(rf"^{t}:", body, re.M), f"missing operational target {t}"


# ---------------------------------------------------------------------------
# OPS-EVAL-2 — SRE / DevOps Capability Model (eval 63): reproducibility,
# environment parity, and enforcement paths for build/runtime artifacts.
# ---------------------------------------------------------------------------

PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "requirements.lock"
API_DOCKERFILE = ROOT / "apps" / "api" / "Dockerfile"
COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"


def test_runtime_deps_all_pinned_in_lock():
    """OPS-EVAL-2-001: ``-c requirements.lock`` only constrains what it lists —
    a runtime dep absent from the lock installs FLOATING (reproducibility
    hole). Every ``project.dependencies`` name must appear pinned."""
    import tomllib

    pp = tomllib.loads(_read(PYPROJECT))
    locked = {
        line.split("==")[0].strip().lower().replace("-", "_")
        for line in _read(LOCK).splitlines()
        if "==" in line
    }
    unpinned = []
    for dep in pp["project"].get("dependencies", []):
        name = re.split(r"[<>=; \[]", dep)[0].strip().lower()
        if name and name.replace("-", "_") not in locked:
            unpinned.append(dep)
    assert not unpinned, f"runtime deps not in requirements.lock (floating): {unpinned}"


def test_api_dockerfile_constrains_installs_with_lock():
    """The production image must install under the audited constraint file."""
    src = _read(API_DOCKERFILE)
    assert "-c requirements.lock" in src, "api Dockerfile installs without lock constraints"
    assert "COPY requirements.lock" in src, "api Dockerfile does not ship the lock"


def test_compose_image_defaults_pinned():
    """OPS-EVAL-2-002: every image: default must carry an explicit tag or be a
    locally-built ${COMPOSE_PROJECT_NAME}-* image — no :latest, no bare names."""
    floating = []
    for f in COMPOSE_DIR.rglob("*.yml"):
        for m in re.finditer(r"^\s+image:\s*(\S+)", _read(f), re.M):
            ref = m.group(1)
            default = re.sub(r"\$\{[^:}]+:-([^}]*)\}", r"\1", ref)
            if default.startswith("${"):
                default = re.sub(r"\$\{[^}]+\}", "", default)
            if "${COMPOSE_PROJECT_NAME" in ref:
                continue  # locally built image — source is the pin
            if ":" not in default:
                floating.append(f"{f.name}: {ref}")
    assert not floating, f"unpinned compose image defaults: {floating}"


def test_env_container_regenerated_in_up_sequence():
    """OPS-EVAL-2-003: .env.container must be GENERATED on every `make up`
    (build_local_env.py), never hand-maintained — the parity mechanism."""
    for mk in MAKEFILES:
        body = _read(mk)
        up = re.search(r"^up:.*?(?=^\S|\Z)", body, re.M | re.S)
        assert up, f"{mk.name}: no up target found"
        assert "build_local_env.py" in up.group(0), (
            f"{mk.name}: up does not regenerate .env.container — env parity drifts"
        )


def test_verify_digests_enforcement_path_exists():
    """warn-only digest check during `up` is acceptable ONLY because the
    blocking opt-in `make verify-digests` remains available."""
    for mk in MAKEFILES:
        body = _read(mk)
        assert re.search(r"^verify-digests:", body, re.M), (
            f"{mk.name}: blocking verify-digests target removed"
        )
        assert "verify_image_digests.py" in body


def test_doctor_checks_critical_subsystems():
    src = _read(ROOT / "scripts" / "maintenance" / "doctor.py")
    for probe in ("docker", "elasticsearch", "redis", "webhook"):
        assert probe in src.lower(), f"doctor lost the {probe} probe"
