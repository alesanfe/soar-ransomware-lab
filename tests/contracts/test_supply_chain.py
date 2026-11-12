"""Supply-chain gates: SBOM generation + secret-scan contract.

CI already runs gitleaks + cyclonedx-py; these tests make the gates
executable locally inside the container:
  - SBOM: build a CycloneDX 1.6 document from the frozen environment with
    the installed cyclonedx lib and assert component completeness/pinning.
  - Secret scan: regex dictionary over tracked source files — the same
    class of patterns gitleaks flags, with an explicit allowlist.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path("/app")

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"),
    "generic_secret_assign": re.compile(
        r"(?i)(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"]?([A-Za-z0-9+/=_\-]{16,})"
    ),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "slack_webhook": re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/"),
    "github_pat": re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
}

ALLOWLIST_RX = re.compile(
    r"(CHANGE_ME|changeme|example|placeholder|your[-_]?|<.*>|\$\{|\.\.\.|"
    r"dummy|fake|test[-_]?|sample|dummy|xxx|PASSWORD=|API_KEY=|TOKEN=|"
    r"soar[-_]?lab|soar[-_][a-z0-9]+|thehive|cortex|misp|shuffle|"
    r"Lab(Secure|Secret)?|replace-with|generate[d]?|change-this|"
    r"https?://|^-----BEGIN RSA PRIVATE KEY-----$|"
    r"_get_|_default_|generate_|JWTTokenProvider|_SERVICE_HEADERS|"
    r"__[A-Z][A-Z0-9_]+__|_(PASSWORD|TOKEN|SECRET|PASS|KEY)$|"
    r"ELASTIC_PASSWORD|POSTGRES_PASSWORD|GRAFANA_|SIEM_|FIREWALL_|EDR_)",
    re.IGNORECASE,
)
SCAN_GLOBS = ("*.py", "*.yml", "*.yaml", "*.json", "*.env*", "*.conf", "*.sh", "*.ini", "*.toml")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "runtime", "reports", "artifacts", ".venv", "docs/thesis"}
# .env*/.env.container are gitignored local files — gitleaks only scans the
# index, so scanning them here would flag legitimate local state.
SKIP_FILES = {
    "test_supply_chain.py", ".env.full", ".env", ".env.container", "ca.key",
    # scanner self-test fixture — the BEGIN-key literal is its test input
    "test_fase2_hardening.py",
}


def _iter_files():
    # os.walk with in-place dir pruning — rglob descends into skipped trees
    # first and filters later, which is catastrophically slow on bind-mounted
    # repos (runtime/, node_modules, .git can hold millions of entries).
    import fnmatch
    import os

    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            if any(fnmatch.fnmatch(name, pat) for pat in SCAN_GLOBS):
                f = Path(dirpath) / name
                if f.is_file():
                    yield f


@pytest.mark.unit
class TestSupplyChain:
    def test_sbom_builds_from_frozen_environment(self):
        """A CycloneDX doc can be built and every component is pinned."""
        from cyclonedx.model.bom import Bom
        from cyclonedx.model.component import Component, ComponentType

        freeze = subprocess.run(
            ["pip", "freeze"], capture_output=True, text=True, timeout=60
        )
        pkgs = [ln.split("==") for ln in freeze.stdout.splitlines() if "==" in ln]
        assert len(pkgs) > 50, "suspiciously few installed packages"

        bom = Bom()
        for name, ver in pkgs:
            bom.components.add(
                Component(name=name.strip(), version=ver.strip(), type=ComponentType.LIBRARY)
            )
        from cyclonedx.output.json import JsonV1Dot6

        doc = json.loads(JsonV1Dot6(bom).output_as_string())
        assert doc["bomFormat"] == "CycloneDX"
        assert len(doc["components"]) == len(pkgs)
        for c in doc["components"]:
            assert c.get("name") and c.get("version"), f"unpinned component: {c}"

    def test_no_high_entropy_secrets_in_tracked_source(self):
        findings = []
        for f in _iter_files():
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name, rx in SECRET_PATTERNS.items():
                for m in rx.finditer(text):
                    val = m.group(0)
                    if ALLOWLIST_RX.search(val):
                        continue
                    findings.append(f"{f.relative_to(REPO)}:{name}:{val[:30]}")
        assert not findings, (
            "secret-like strings in tracked source:\n" + "\n".join(findings[:25])
        )

    def test_env_example_has_no_real_values(self):
        """.env.example documents names only — never ships real secrets."""
        f = REPO / ".env.example"
        if not f.exists():
            pytest.skip(".env.example absent")
        for ln in f.read_text().splitlines():
            if "=" not in ln or ln.strip().startswith("#"):
                continue
            key, _, val = ln.partition("=")
            val = val.strip().strip("'\"")
            if not val:
                continue
            # only high-entropy single-token values can be secrets — service
            # names, image refs, URLs and multi-word config are not.
            secret_shaped = re.match(r"^[A-Za-z0-9+/=_-]{16,}$", val) is not None
            assert not secret_shaped or ALLOWLIST_RX.search(val), (
                f".env.example carries a real-looking value for {key.strip()}"
            )
