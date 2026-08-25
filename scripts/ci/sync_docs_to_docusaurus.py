#!/usr/bin/env python3
"""Sync docs/ → apps/docs-site/docs/

Copia los documentos Markdown de docs/ al directorio de Docusaurus,
organizándolos en la estructura de carpetas que espera el sidebar.

Estructura de destino:
  apps/docs-site/docs/
    intro.md                    ← docs/index.md
    getting_started/            ← docs/01-getting-started.md
    architecture/               ← docs/02-architecture.md
    integrations/               ← docs/03-api-and-integrations.md
    operations/                 ← docs/04-operations.md
    testing/                    ← docs/05-testing.md
    project/                    ← docs/06-project-management.md
    GLOSSARY/                   ← docs/glossary.md
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DIR = REPO_ROOT / "docs"
TARGET_DIR = REPO_ROOT / "apps" / "docs-site" / "docs"

# Mapping: source file → (target dir, target filename)
DOC_MAPPING = {
    "index.md": ("intro.md", None),
    "01-getting-started.md": ("getting_started", "intro.md"),
    "02-architecture.md": ("architecture", "overview.md"),
    "03-api-and-integrations.md": ("integrations", "intro.md"),
    "04-operations.md": ("operations", "intro.md"),
    "05-testing.md": ("testing", "intro.md"),
    "06-project-management.md": ("project", "intro.md"),
    "glossary.md": ("GLOSSARY", "intro.md"),
}


def fix_internal_links(content: str) -> str:
    """Fix internal links for Docusaurus structure.

    Docusaurus uses relative links within docs/ directory. Adjust links
    like [text](01-getting-started.md) to the new paths.
    """
    # Map old filenames to new paths
    link_map = {
        "01-getting-started.md": "getting_started/intro",
        "02-architecture.md": "architecture/overview",
        "03-api-and-integrations.md": "integrations/intro",
        "04-operations.md": "operations/intro",
        "05-testing.md": "testing/intro",
        "06-project-management.md": "project/intro",
        "glossary.md": "GLOSSARY/intro",
        "index.md": "intro",
    }

    # Replace markdown links [text](filename.md)
    for old, new in link_map.items():
        content = re.sub(
            rf"\(\s*{re.escape(old)}\s*\)",
            f"({new}.md)",
            content,
        )

    return content


def sync_docs() -> int:
    """Sync docs to Docusaurus docs directory."""
    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return 1

    # Clear target (except reports/ which is synced separately)
    if TARGET_DIR.exists():
        for item in TARGET_DIR.iterdir():
            if item.name == "reports":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        TARGET_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    for source_name, (target_path, target_filename) in DOC_MAPPING.items():
        source_file = SOURCE_DIR / source_name
        if not source_file.exists():
            print(f"  SKIP: {source_name} (not found)")
            continue

        if target_filename is None:
            # Direct file in target root
            target_file = TARGET_DIR / target_path
        else:
            target_dir = TARGET_DIR / target_path
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_filename

        content = source_file.read_text(encoding="utf-8")
        content = fix_internal_links(content)
        target_file.write_text(content, encoding="utf-8")
        print(f"  COPIED: {source_name} -> {target_file.relative_to(REPO_ROOT)}")
        copied += 1

    # Create _category_.json for each subdirectory
    categories = {
        "getting_started": ("Getting Started", 1),
        "architecture": ("Architecture", 2),
        "integrations": ("Integrations", 3),
        "operations": ("Operations", 4),
        "testing": ("Testing", 5),
        "project": ("Project Management", 6),
        "GLOSSARY": ("Glossary", 7),
    }
    import json

    for dirname, (label, position) in categories.items():
        cat_file = TARGET_DIR / dirname / "_category_.json"
        cat_file.write_text(
            json.dumps({"label": label, "position": position, "collapsed": False}),
            encoding="utf-8",
        )

    print(f"\nSynced {copied} documents to {TARGET_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync_docs())
