"""Supply-chain / CI-CD regression gates (docs/31-eval-supply-chain.md).

SC-EVAL findings pinned as architecture gates:
  SC-EVAL-001 every GitHub Actions `uses:` ref is commit-SHA pinned
  SC-EVAL-002 every workflow declares top-level least-privilege permissions
  SC-EVAL-003 no pull_request_target / risky event interpolation
  SC-EVAL-004 Dependabot covers every active Dockerfile directory
  SC-EVAL-005 pinned release pipeline: SLSA provenance + SBOM + cosign
  SC-EVAL-006 requirements.lock exists, is complete vs pyproject runtime
             deps and satisfies their version ranges
Positive gates: least-privilege permissions already present on most
workflows, pinned pip installs, OIDC id-token only where required.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WF_DIR = ROOT / ".github" / "workflows"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
LOCK = ROOT / "requirements.lock"
PYPROJECT = ROOT / "pyproject.toml"
API_DOCKERFILE = ROOT / "apps" / "api" / "Dockerfile"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Dockerfiles kept for historical compat only (robtex analyzers are
# deprecated — see AGENTS.md); Dependabot intentionally skips them.
DEPRECATED_DOCKERFILE_DIRS = {"infra/docker/cortex-analyzers/robtex-patched",
                              "infra/docker/cortex-analyzers/robtex-forward-patched",
                              "infra/docker/cortex-analyzers/robtex-reverse-patched"}


def _workflows() -> dict[str, dict]:
    return {p.name: yaml.safe_load(p.read_text(encoding="utf-8")) for p in WF_DIR.glob("*.yml")}


def _uses_refs() -> list[tuple[str, str]]:
    refs = []
    for p in WF_DIR.glob("*.yml"):
        for m in re.finditer(r"uses:\s*([^\s#]+)", p.read_text(encoding="utf-8")):
            refs.append((p.name, m.group(1)))
    return refs


def test_all_action_uses_sha_pinned():
    """SC-EVAL-001: mutable tags (@v4/@main) are a substitution vector."""
    bad = []
    for wf, ref in _uses_refs():
        if ref.startswith(("docker://", "./")):
            continue
        _, _, pinned = ref.rpartition("@")
        if not SHA_RE.match(pinned):
            bad.append(f"{wf}: {ref}")
    assert not bad, f"non-SHA-pinned action refs: {bad}"


def test_all_workflows_declare_permissions():
    """SC-EVAL-002: absent top-level permissions = full GITHUB_TOKEN."""
    for name, wf in _workflows().items():
        assert "permissions" in wf, f"{name} lacks top-level permissions block"


def test_no_pull_request_target():
    """SC-EVAL-003: pull_request_target runs fork code with repo secrets."""
    for name, wf in _workflows().items():
        on = wf.get(True) or wf.get("on") or {}
        triggers = on if isinstance(on, list) else list(on.keys())
        assert "pull_request_target" not in triggers, f"{name} uses pull_request_target"


def test_no_event_data_interpolated_into_run():
    """SC-EVAL-003: ${{ github.event.* }} in run: = script injection."""
    for p in WF_DIR.glob("*.yml"):
        for m in re.finditer(r"run:.*\$\{\{\s*github\.event\.", p.read_text(encoding="utf-8")):
            raise AssertionError(f"{p.name}: event data interpolated into run step")


def test_dependabot_covers_all_dockerfile_dirs():
    """SC-EVAL-004: every active Dockerfile dir gets weekly docker bumps."""
    dep = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    covered = {u["directory"].strip("/") for u in dep["updates"] if u["package-ecosystem"] == "docker"}
    # os.walk with dir-pruning — rglob would descend into node_modules/
    # before the filter can exclude it (OOM under container limits).
    import os

    skip = {"node_modules", "__pycache__", "runtime", ".git"}
    actual = set()
    for base in ("apps", "infra", "src"):
        for dirpath, dirnames, filenames in os.walk(ROOT / base):
            dirnames[:] = [d for d in dirnames if d not in skip]
            if "Dockerfile" in filenames:
                actual.add(str(Path(dirpath).relative_to(ROOT)).replace("\\", "/"))
    missing = actual - covered - DEPRECATED_DOCKERFILE_DIRS
    assert not missing, f"Dockerfile dirs without Dependabot coverage: {missing}"


def test_dependabot_covers_pip_npm_actions():
    dep = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    eco = {u["package-ecosystem"] for u in dep["updates"]}
    assert {"pip", "npm", "github-actions", "docker"} <= eco


def test_release_pipeline_provenance_signing():
    """SC-EVAL-005: release emits SLSA provenance + SBOM + cosign sign/verify."""
    rel = (WF_DIR / "release.yml").read_text(encoding="utf-8")
    for needle in ("provenance: mode=max", "sbom: true", "cosign sign", "cosign verify"):
        assert needle in rel, f"release.yml missing '{needle}'"


def test_sbom_generated_in_ci_and_release():
    ci = (WF_DIR / "ci.yml").read_text(encoding="utf-8")
    rel = (WF_DIR / "release.yml").read_text(encoding="utf-8")
    assert "cyclonedx" in ci, "ci.yml lacks CycloneDX SBOM job"
    assert "cyclonedx" in rel, "release.yml lacks CycloneDX SBOM step"


def test_requirements_lock_complete_and_fresh():
    """SC-EVAL-006: lock covers every runtime dep and satisfies its range."""
    from packaging.requirements import Requirement
    from packaging.version import Version

    lock = {
        line.split("==")[0].strip().lower(): line.split("==")[1].strip()
        for line in LOCK.read_text().splitlines()
        if "==" in line and not line.startswith("#")
    }
    assert len(lock) >= 30, f"lock suspiciously small: {len(lock)} entries"
    deps = [Requirement(d) for d in tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]]
    missing, conflicts = [], []
    for d in deps:
        name = d.name.lower()
        if name not in lock:
            # platform-conditional deps absent from a linux-resolved lock are OK
            if d.marker is None or "sys_platform" not in str(d.marker):
                missing.append(d.name)
            continue
        if Version(lock[name]) not in d.specifier:
            conflicts.append(f"{d.name}=={lock[name]} vs {d.specifier}")
    assert not missing, f"runtime deps missing from lock: {missing}"
    assert not conflicts, f"lock conflicts with pyproject ranges: {conflicts}"


def test_api_dockerfile_uses_lock_constraints():
    """SC-EVAL-006: image build pins runtime deps via -c requirements.lock."""
    text = API_DOCKERFILE.read_text(encoding="utf-8")
    assert "COPY requirements.lock ." in text
    assert "-c requirements.lock" in text


def test_no_unpinned_pip_installs_in_workflows():
    """Standalone `pip install <pkg>` (no ==) in CI pulls arbitrary latest."""
    bad = []
    for p in WF_DIR.glob("*.yml"):
        for m in re.finditer(r"pip install (?!.*(==|-e |--upgrade|-r |-c ))(\S+)",
                             p.read_text(encoding="utf-8")):
            bad.append(f"{p.name}: pip install {m.group(2)}")
    assert not bad, f"unpinned pip installs: {bad}"


def test_workflow_yaml_parses():
    parsed = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in WF_DIR.glob("*.yml")]
    assert parsed and all(isinstance(w, dict) for w in parsed)


def test_id_token_write_only_where_needed():
    """OIDC id-token: write only justified on release/pages/scorecard."""
    allowed = {"release.yml", "deploy-docs.yml", "scorecard.yml", "quality.yml"}
    for name, wf in _workflows().items():
        perms = wf.get("permissions") or {}
        blob = yaml.dump(perms)
        for job in (wf.get("jobs") or {}).values():
            blob += yaml.dump((job or {}).get("permissions") or {})
        if "id-token: write" in blob:
            assert name in allowed, f"{name} has id-token: write without justification"


class TestBaseImagePinning:
    """SSDF PW.4 / SLSA L3 — Dockerfile FROMs must be digest-pinned."""

    DOCKERFILES = [
        "apps/api/Dockerfile",
        "apps/docs-site/Dockerfile",
        "apps/web-management/Dockerfile",
        "infra/docker/taxii/Dockerfile",
    ]

    def test_all_froms_digest_pinned(self):
        for f in self.DOCKERFILES:
            for m in re.finditer(r"^FROM (\S+)", Path(f).read_text(encoding="utf-8"), re.M):
                ref = m.group(1)
                if ":" in ref or "@" in ref:  # skip stage aliases (deps, builder)
                    assert "@sha256:" in ref, f"{f}: unpinned base image {ref}"


class TestReleaseProvenance:
    """SLSA L3 — signing + attestation self-checks must stay in release.yml."""

    def test_cosign_sign_verify_attest(self):
        rel = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
        assert "cosign sign --yes" in rel
        assert "cosign verify " in rel
        assert "verify-attestation" in rel and "slsaprovenance" in rel
        assert "provenance: mode=max" in rel and "sbom: true" in rel
        assert "certificate-oidc-issuer" in rel
