#!/usr/bin/env python3
"""CI checks for documentation consistency."""

import json
import logging
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)
errors = []


def err(msg: str):
    logger.error(f"ERROR: {msg}")
    errors.append(msg)


# 1. OpenAPI diff: exported spec must match docs/api/openapi.json
spec_path = ROOT / "docs" / "api" / "openapi.json"
baseline_path = ROOT / "tests" / "baseline" / "openapi.json"
if spec_path.exists() and baseline_path.exists():
    if spec_path.read_text() != baseline_path.read_text():
        err("docs/api/openapi.json and baseline/openapi.json differ")
else:
    err("openapi.json missing in docs/api or tests/baseline")

# 2. Test inventory exists and is parseable
inv = ROOT / "tests" / "baseline" / "tests_inventory.json"
if inv.exists():
    try:
        json.loads(inv.read_text())
    except Exception as e:
        err(f"tests_inventory.json not valid JSON: {e}")
else:
    err("tests/baseline/tests_inventory.json missing")

# 3. Pytest collection smoke test
res = subprocess.run(
    [sys.executable, "-m", "pytest", "--collect-only", "-q"],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
if res.returncode != 0:
    err("pytest --collect-only failed")
elif "tests collected" not in res.stdout:
    err("pytest collection count unexpected; see pytest_collect_latest.txt")

# 4. Banned patterns/outdated references in docs
#    (skip legacy audit files and remediation task list)
legacy_dirs = {ROOT / "docs" / "audit" / "legacy", ROOT / "docs" / "audit" / "legacy" / ""}
remediation_task_list = ROOT / "docs" / "project" / "documentation_remediation_tasks.md"
banned = {
    r"(?<![A-Za-z0-9_])1001 passed(?![A-Za-z0-9_])": "outdated test count '1001 passed'",
    r"(?<![A-Za-z0-9_])SiemToken(?![A-Za-z0-9_])": "static secret placeholder SiemToken",
    r"(?<![A-Za-z0-9_])apps/api/(?!Dockerfile|requirements\.txt)": (
        "legacy apps/api path (use src/soar_lab/interfaces/api/)"
    ),
    r"http://soar\.local:8000": "old proxied URL (use https://soar.local/api)",
    r"https?://soar\.local/shuffle": "Shuffle UI subpath not supported via Nginx",
    r"localhost:8080\b(?!/health)": "old docs-site/API port 8080 (use 8000/8086)",
}
for md in (ROOT / "docs").rglob("*.md"):
    if "legacy" in md.parts or md == remediation_task_list:
        continue
    text = md.read_text(encoding="utf-8", errors="ignore")
    for pat, msg in banned.items():
        if re.search(pat, text):
            err(f"{md.relative_to(ROOT)} contains banned reference: {msg}")

# 5. Mermaid block validation
mermaid_keywords = (
    "flowchart",
    "graph ",
    "graph\t",
    "graph\n",
    "sequenceDiagram",
    "gantt",
    "classDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "journey",
    "gitGraph",
    "pie",
    "requirementDiagram",
    "C4Context",
    "mindmap",
    "timeline",
    "sankey",
    "xychart-beta",
    "block-beta",
)
mermaid_pat = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
for md in (ROOT / "docs").rglob("*.md"):
    text = md.read_text(encoding="utf-8", errors="ignore")
    for i, m in enumerate(mermaid_pat.finditer(text), 1):
        body = m.group(1).strip()
        if not body:
            err(f"{md.relative_to(ROOT)} has empty Mermaid block #{i}")
            continue
        first_line = body.splitlines()[0].strip()
        if not any(first_line.startswith(kw) for kw in mermaid_keywords):
            err(
                f"{md.relative_to(ROOT)} Mermaid block #{i}"
                f" starts with unknown directive: {first_line[:40]}"
            )

if errors:
    print(f"\n{len(errors)} documentation check(s) failed")
    sys.exit(1)
print("Documentation quality checks passed")
