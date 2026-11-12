"""Architecture gates — test suite as an asset (eval 41).

Static invariants for the quality of the test suite itself, documented in
``docs/41-eval-test-suite.md``: the E2E oracle ratchet must stay seeded and
cover zero-oracle tests, the workflow exporter must scrub live secrets, and
the mutation gate must remain bounded.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "quality" / "e2e_oracle_audit.py"
BASELINE = ROOT / "tests" / "e2e" / "oracle_baseline.json"
EXPORT = ROOT / "scripts" / "maintenance" / "export_workflows.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"
PYTEST_INI = ROOT / "pytest.ini"
PLAYBOOKS = ROOT / "playbooks"
SUPPLY_CHAIN = ROOT / "tests" / "contracts" / "test_supply_chain.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# --- Oracle audit ratchet ----------------------------------------------------

def test_oracle_baseline_exists_and_seeded():
    data = json.loads(_read(BASELINE))
    fps = data.get("fingerprints", [])
    assert len(fps) >= 50, "oracle baseline missing or too small — ratchet not seeded"


def test_oracle_audit_detects_zero_oracle_functions():
    src = _read(AUDIT)
    assert '"no_oracle"' in src or "'no_oracle'" in src
    assert "_has_any_oracle" in src


def test_oracle_audit_scans_for_swallowed_asserts():
    src = _read(AUDIT)
    for category in ("except_pass", "permissive_status", "arbitrary_sleep", "swallowed_assert"):
        assert category in src, f"audit lost check for {category}"


# --- Secret hygiene in tracked GitOps exports ---------------------------------

def test_exporter_scrubs_live_secrets():
    src = _read(EXPORT)
    assert "_scrub" in src, "export_workflows.py lost the secret-scrub step"
    assert "__INTERNAL_SERVICE_TOKEN__" in src or "_secret_placeholders" in src


def test_playbooks_carry_placeholders_not_live_tokens():
    """Tracked playbook exports must use __VAR__ placeholders, never live values."""
    for pb in PLAYBOOKS.glob("*.json"):
        body = _read(pb)
        for m in re.finditer(r'"(?:X-Service-Token|Authorization)"\s*:\s*"([^"]+)"', body):
            value = m.group(1)
            assert re.fullmatch(r"__[A-Z_]+__", value), (
                f"{pb.name} embeds a live credential header — scrub to placeholder"
            )


def test_supply_chain_scan_has_secret_allowlist_narrow():
    src = _read(SUPPLY_CHAIN)
    assert "ALLOWLIST" in src or "allowlist" in src.lower()


# --- Mutation gate stays bounded ----------------------------------------------

def test_mutation_gate_bounded_in_ci():
    lines = _read(CI).splitlines()
    for i, line in enumerate(lines):
        if "mutmut run" in line:
            window = " ".join(lines[i : i + 4])
            assert "--paths-to-mutate" in window, (
                "CI runs unbounded mutation testing — scope with --paths-to-mutate"
            )


def test_pytest_enforces_coverage_floor():
    """The 80% coverage floor must be enforced by config or Makefile flags."""
    sources = [
        ROOT / ".coveragerc",
        ROOT / "pyproject.toml",
        ROOT / "Makefile.win",
        ROOT / "Makefile.linux",
    ]
    found = False
    for src_path in sources:
        if src_path.exists():
            body = _read(src_path)
            m = re.search(r"(?:fail_under|cov-fail-under)\s*[= ]\s*(\d+)", body)
            if m and int(m.group(1)) >= 80:
                found = True
                break
    assert found, "coverage floor >=80% not found in .coveragerc/pyproject/Makefiles"


# --- Weak-oracle regression ----------------------------------------------------

def test_no_pass_only_test_bodies_in_atomic_suite():
    """TST-EVAL: no atomic test may be a bare `pass`/docstring placeholder."""
    atomic = ROOT / "tests" / "atomic"
    offenders = []
    for f in atomic.rglob("test_*.py"):
        tree = _read(f)
        for m in re.finditer(r"def (test_\w+)\([^)]*\):\s*\n((?:\s+.+\n)+)", tree):
            body = m.group(2)
            code_lines = [
                ln for ln in body.splitlines()
                if ln.strip() and not ln.strip().startswith(("#", '"""', "'''"))
            ]
            if not code_lines or all(ln.strip() in ("pass", "...") for ln in code_lines):
                offenders.append(f"{f.name}::{m.group(1)}")
    assert not offenders, f"hollow test bodies: {offenders}"


# --- TST-EVAL-2 (eval 60): ISO 29119 reporting + coverage criteria ------------

def test_ci_emits_junit_reports_for_test_jobs():
    """ISO 29119 test completion reporting: every CI test run must emit a
    JUnit artifact so results are preserved per-run (not console-only)."""
    src = _read(CI)
    for suite in ("tests/unit/", "tests/integration/", "tests/atomic"):
        assert suite in src, suite
    assert src.count("--junitxml=reports/junit/") >= 3
    assert src.count("name: junit-") >= 3


def test_branch_coverage_enabled():
    """Line-only coverage hides untested branch paths (ISO 29119 coverage
    criteria). .coveragerc must keep branch=True."""
    src = _read(ROOT / ".coveragerc")
    assert re.search(r"^branch\s*=\s*True", src, re.M)


def test_coverage_ratchet_declared():
    """The PR-level ratchet lives in codecov.yml — project regression and
    patch target must be declared, not left to defaults."""
    codecov = ROOT / "codecov.yml"
    assert codecov.exists(), "codecov.yml missing — ratchet not declared"
    src = _read(codecov)
    assert "project:" in src and "patch:" in src and "target:" in src


def test_no_flaky_retry_plugin():
    """SAMM verification posture: flaky tests are defects, not retries.
    pytest-rerunfailures (or equivalent) must not be a dependency —
    masking flakiness hides real nondeterminism bugs."""
    for req in ("requirements.lock", "requirements-dev.lock", "requirements-test.lock"):
        p = ROOT / req
        if p.exists():
            assert "rerunfailures" not in _read(p).lower(), req
    assert "rerun" not in _read(PYTEST_INI).lower()


def test_secret_scanning_in_ci():
    """NIST SSDF RV.3 / SAMM: secret detection must run in the pipeline,
    not only locally (TruffleHog + custom scanner)."""
    src = _read(CI)
    assert "trufflehog" in src.lower()
    assert "scan_secrets" in src
