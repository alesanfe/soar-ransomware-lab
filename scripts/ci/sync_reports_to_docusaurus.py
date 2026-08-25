#!/usr/bin/env python3
"""Sync reports/ → apps/docs-site/docs/reports/

Copia los reportes generados (quality, mutmut, e2e, test-review, holistic)
al directorio de Docusaurus para que se publiquen en GitHub Pages.

Estructura de destino:
  apps/docs-site/docs/reports/
    intro.md                        ← índice de reports
    quality/quality-summary.md       ← reports/quality/quality-summary.md
    test-review/test_review_report.md ← reports/test-review/test_review_report.md
    holistic/holistic_review_report.md ← reports/holistic/holistic_review_report.md
    mutmut/mutation_report.md        ← reports/mutmut/mutation_report.md (si existe)
    e2e/                             ← reports/e2e/*.md (si existen)
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
TARGET_DIR = REPO_ROOT / "apps" / "docs-site" / "docs" / "reports"

# Mapping: source dir → target dir
REPORT_MAPPING = {
    "quality": "quality",
    "test-review": "test-review",
    "holistic": "holistic",
    "mutmut": "mutmut",
    "e2e": "e2e",
}

INTRO_CONTENT = """---
id: reports-intro
title: Reports
sidebar_label: Reports
slug: /reports/
---

# Quality Reports

This section contains automatically generated quality reports from the CI/CD pipeline.

## Available Reports

| Report | Description | Source |
|--------|-------------|--------|
| [Quality](quality/quality-summary) | Code quality metrics (radon, bandit) | `make quality` |
| [Test Review](test-review/test_review_report) | 7-dimension test review | `make test-review` |
| [Holistic Review](holistic/holistic_review_report) | Holistic Radar | `make holistic-review` |
| [Mutation Testing](mutmut/mutation_report) | Mutation testing results | `make mutation` |
| [E2E Tests](e2e/) | End-to-end test results | `make test-e2e` |

## Generation

Reports are generated on every push to `main` via the
[Quality Suite workflow](https://github.com/alesanfe/soar-ransomware-lab/actions/workflows/quality.yml)
and deployed to this site via the
[Deploy Docs workflow](https://github.com/alesanfe/soar-ransomware-lab/actions/workflows/deploy-docs.yml).
"""


def sync_reports() -> int:
    """Sync reports to Docusaurus docs/reports/ directory."""
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Write intro
    intro_file = TARGET_DIR / "intro.md"
    intro_file.write_text(INTRO_CONTENT, encoding="utf-8")
    print("  CREATED: intro.md")

    copied = 0
    for source_subdir, target_subdir in REPORT_MAPPING.items():
        source_dir = REPORTS_DIR / source_subdir
        if not source_dir.exists():
            print(f"  SKIP: {source_subdir}/ (not found)")
            continue

        target_subdir_path = TARGET_DIR / target_subdir
        target_subdir_path.mkdir(parents=True, exist_ok=True)

        # Copy all .md files
        for md_file in source_dir.glob("*.md"):
            target_file = target_subdir_path / md_file.name
            shutil.copy2(md_file, target_file)
            print(f"  COPIED: {source_subdir}/{md_file.name}")
            copied += 1

        # Copy all .json files (for e2e reports)
        for json_file in source_dir.glob("*.json"):
            target_file = target_subdir_path / json_file.name
            shutil.copy2(json_file, target_file)
            print(f"  COPIED: {source_subdir}/{json_file.name}")
            copied += 1

    # Create _category_.json for reports and subdirectories
    import json

    categories = {
        "": ("Reports", 8),
        "quality": ("Quality", 1),
        "test-review": ("Test Review", 2),
        "holistic": ("Holistic Review", 3),
        "mutmut": ("Mutation Testing", 4),
        "e2e": ("E2E Tests", 5),
    }
    for subdir, (label, position) in categories.items():
        cat_dir = TARGET_DIR / subdir if subdir else TARGET_DIR
        cat_dir.mkdir(parents=True, exist_ok=True)
        cat_file = cat_dir / "_category_.json"
        cat_file.write_text(
            json.dumps({"label": label, "position": position, "collapsed": False}),
            encoding="utf-8",
        )

    print(f"\nSynced {copied} report files to {TARGET_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync_reports())
