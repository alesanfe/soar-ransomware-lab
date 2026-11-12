"""Architecture gates — RESIDUAL-HARDENING (post-evaluation debt closure).

Guards the fixes applied while closing the residuals documented in each
docs/*-eval-*.md:

- CI-EVAL-001: ci.yml must run the local-only suites (atomic, architecture,
  security, contract(s), general, quality) — previously only unit/integration
  ran, so red tests in those suites survived undetected.
- OPS-EVAL-002: doctor.py must probe Redis via TLS (plaintext ping always
  fails on the TLS-only listener and produced a false WARN).
- DOC-EVAL-004: a committed lychee.toml config + a blocking offline link
  check (with anchors) in docs-lint.
- DOC-EVAL-005: Docusaurus must fail the build on broken links/anchors.
- TST-EVAL-013: coverage-quality tests must skip explicitly (module-level,
  with the subprocess output) when coverage.xml cannot be produced — never
  silently pass or hang.
- TST-EVAL-014: pip-audit results must be fetched once per module via
  module-scoped fixtures, not re-run per test (each call bootstraps a venv
  and queries OSV — ~4x slowdown).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"
DOCTOR = ROOT / "scripts" / "maintenance" / "doctor.py"
LYCHEE_TOML = ROOT / "lychee.toml"
DUSAURUS_CFG = ROOT / "apps" / "docs-site" / "docusaurus.config.js"
COVERAGE_TESTS = ROOT / "tests" / "quality" / "test_coverage_quality.py"
DEPSEC_TESTS = ROOT / "tests" / "quality" / "test_dependency_security.py"
MAKEFILES = [ROOT / "Makefile.linux", ROOT / "Makefile.win"]


class TestCILocalSuites:
    """CI-EVAL-001 — the pure-local suites run in CI."""

    def test_ci_runs_atomic_and_architecture(self):
        yml = CI.read_text(encoding="utf-8")
        assert "tests/atomic" in yml
        assert "tests/architecture" in yml

    def test_ci_runs_security_and_contracts(self):
        yml = CI.read_text(encoding="utf-8")
        assert "tests/security" in yml
        assert "tests/contract" in yml  # covers tests/contract + tests/contracts

    def test_ci_runs_general_and_quality(self):
        yml = CI.read_text(encoding="utf-8")
        assert "tests/general" in yml
        assert "tests/quality" in yml

    def test_local_suites_deselect_external(self):
        yml = CI.read_text(encoding="utf-8")
        assert 'not requires_docker and not requires_external' in yml


class TestDoctorRedisTLS:
    """OPS-EVAL-002 — redis probe uses the TLS listener."""

    def test_redis_probe_uses_tls(self):
        src = DOCTOR.read_text(encoding="utf-8")
        check_redis = src[src.index("def check_redis"):src.index("CHECKS")]
        assert '"--tls"' in check_redis or "'--tls'" in check_redis
        assert "/etc/redis/tls/ca.crt" in check_redis


class TestDocsLinkHardening:
    """DOC-EVAL-004/005 — committed lychee config + blocking checks."""

    def test_lychee_toml_committed_and_sane(self):
        assert LYCHEE_TOML.exists(), "lychee.toml must be committed"
        cfg = LYCHEE_TOML.read_text(encoding="utf-8")
        assert "exclude_all_private = true" in cfg
        assert "include_fragments = true" in cfg

    def test_docs_lint_runs_lychee_blocking_offline(self):
        for mk in MAKEFILES:
            content = mk.read_text(encoding="utf-8")
            docs_lint = content[content.index("docs-lint:"):]
            docs_lint = docs_lint[: docs_lint.index("\n\n")]
            assert "lychee --offline --config lychee.toml" in docs_lint, (
                f"{mk.name}: docs-lint must run the blocking offline lychee "
                "check with the committed config"
            )
            # Blocking = recipe line without the '-' ignore-errors prefix.
            assert not re.search(r"^\s+-@\S*.*lychee --offline", docs_lint, re.M), (
                f"{mk.name}: lychee line still marked non-blocking"
            )

    def test_docusaurus_throws_on_broken_links(self):
        cfg = DUSAURUS_CFG.read_text(encoding="utf-8")
        assert "onBrokenLinks: 'throw'" in cfg
        assert "onBrokenMarkdownLinks: 'throw'" in cfg
        assert "onBrokenAnchors: 'throw'" in cfg


class TestQualitySuiteEfficiency:
    """TST-EVAL-013/014 — quality tests bound their external calls."""

    def test_coverage_fixture_skips_module_level_on_failure(self):
        src = COVERAGE_TESTS.read_text(encoding="utf-8")
        assert "allow_module_level=True" in src
        assert "TimeoutExpired" in src

    def test_pip_audit_is_module_scoped(self):
        src = DEPSEC_TESTS.read_text(encoding="utf-8")
        assert src.count('scope="module"') >= 2, (
            "env_audit + lock_audit must be module-scoped fixtures"
        )
        # No test body calls _run_pip_audit directly anymore.
        test_bodies = re.findall(r"def test_\w+\(.*?\):.*?(?=\n    def |\Z)", src, re.S)
        for body in test_bodies:
            assert "_run_pip_audit(" not in body, (
                "a test calls _run_pip_audit directly — must use the "
                "module-scoped fixtures"
            )


# ---------------------------------------------------------------------------
# RH-EVAL-2 — attack surface + debt sweep (eval 64, CIS / NIST 800-53 /
# ISO 27001): supported base branches, zero debt markers, no privileged
# escape hatches in compose.
# ---------------------------------------------------------------------------

COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"
SRC = ROOT / "src" / "soar_lab"


class TestSupportedBaseBranches:
    """RH-EVAL-2-001: the public edge ran nginx:1.25-alpine — a mainline
    branch that went EOL while internal apps were already on 1.27 stable
    (WEB-EVAL-007). The most exposed component must not drift behind."""

    _EOL_NGINX = re.compile(r"nginx:1\.(2[0-5]|[01]\d)(?!\d)")

    def test_no_eol_nginx_refs_anywhere(self):
        offenders = []
        for f in list(COMPOSE_DIR.rglob("*.yml")) + [
            ROOT / n for n in (".env", ".env.example", ".env.full", ".env.testing", ".env.container")
            if (ROOT / n).exists()
        ]:
            body = f.read_text(encoding="utf-8", errors="replace")
            if self._EOL_NGINX.search(body):
                offenders.append(f.name)
        assert not offenders, f"EOL nginx branch referenced in: {offenders}"

    def test_edge_image_is_supported_stable(self):
        for f in (COMPOSE_DIR / "docker-compose.api.yml", COMPOSE_DIR / "docker-compose.core.yml"):
            m = re.search(r"NGINX_IMAGE:-nginx:(\d+)\.(\d+)", f.read_text(encoding="utf-8"))
            assert m, f"{f.name}: NGINX_IMAGE default missing"
            assert int(m.group(2)) >= 26, f"{f.name}: nginx 1.{m.group(2)} is below stable line"


class TestDebtMarkers:
    """Zero-debt invariant: no TODO/FIXME/XXX/HACK comment markers may
    accumulate in src/. Bare-comment match only — string literals (e.g.
    the scanner's own pattern list) are not debt."""

    def test_no_debt_comment_markers_in_src(self):
        marker = re.compile(r"#\s*(TODO|FIXME|XXX|HACK)\b")
        offenders = [
            str(f.relative_to(ROOT))
            for f in SRC.rglob("*.py")
            if marker.search(f.read_text(encoding="utf-8", errors="replace"))
        ]
        assert not offenders, f"debt comment markers introduced: {offenders}"


class TestNoPrivilegedEscapeHatches:
    """CIS 5.x: no container escapes the least-privilege posture via
    privileged:, host namespaces, or a root user in the hardened profile."""

    def test_no_privileged_or_host_modes(self):
        banned = re.compile(r"^\s*(privileged:\s*true|network_mode:\s*host|pid:\s*host)", re.M)
        offenders = [f.name for f in COMPOSE_DIR.rglob("*.yml") if banned.search(f.read_text(encoding="utf-8"))]
        assert not offenders, f"privileged/host escape hatch in: {offenders}"

    def test_root_users_only_in_lab_profile(self):
        """`user: root` may exist only in the relaxed LAB files — the
        hardened overlay must override every one to a named uid."""
        hardened = (COMPOSE_DIR / "docker-compose.hardened.yml").read_text(encoding="utf-8")
        api = (COMPOSE_DIR / "docker-compose.api.yml").read_text(encoding="utf-8")
        assert re.search(r'user:\s*"?redis"?', hardened), "redis root not overridden in hardened"
        assert re.search(r"user:\s*\"\$\{API_UID", hardened), "api root not overridden in hardened"
        assert "user: root" in api, "sanity: lab api keeps root (hardened overrides)"
