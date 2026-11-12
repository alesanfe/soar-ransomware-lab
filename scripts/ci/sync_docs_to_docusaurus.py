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


def _is_eval_doc(name: str) -> bool:
    return bool(re.match(r"^\d+-eval-", name) or re.match(r"^\d+-.*eval", name))


def _top_level_dests() -> dict[str, str]:
    """Link-path → published path (relative to site docs root) for every
    top-level ``docs/*.md`` — the single source both fixers and emitters
    agree on, so a renamed category can't silently break links."""
    dests: dict[str, str] = {}
    for f in SOURCE_DIR.glob("*.md"):
        name = f.name
        if name in DOC_MAPPING:
            tp, tf = DOC_MAPPING[name]
            dests[name] = tp if tf is None else f"{tp}/{tf}"
        elif _is_eval_doc(name):
            dests[name] = f"evaluations/{name}"
        else:
            dests[name] = f"resources/{name}"
    # Subtree passthroughs: links like ](adr/0001-x.md) or ](runbooks/y.md)
    for sub in ("adr", "runbooks"):
        base = SOURCE_DIR / sub
        if base.exists():
            for f in base.rglob("*.md"):
                rel = f.relative_to(SOURCE_DIR).as_posix()
                dests[rel] = rel
    return dests


def _fix_links(content: str, depth: int, allow_dot_prefix: bool = True) -> str:
    """Rewrite ``](doc.md)`` links for a file emitted at *depth* below the
    site docs root. Depth-aware because relative links resolve against the
    file's own directory: a doc in ``resources/`` needs ``../`` to reach
    ``evaluations/``, one in ``adr/sub/`` needs ``../../``.

    ``allow_dot_prefix`` matches ``](./README.md)`` — valid from top-level
    source docs but a *sibling* link inside passthrough subdirs (adr/,
    runbooks/), where it must stay untouched.
    """
    prefix = "../" * depth
    opt_dot = r"(?:\./)?" if allow_dot_prefix else ""
    for old, dest in _top_level_dests().items():
        content = re.sub(
            rf"\(\s*{opt_dot}{re.escape(old)}\s*\)",
            f"({prefix}{dest})",
            content,
        )
    return content


def sync_extra_docs() -> int:
    """DOC-EVAL-2-001: publish the REST of docs/ under organized categories.

    The curated mapping above lands only 7 docs; without this the evals,
    ADRs and runbooks were wiped from the Pages build on every sync
    (``shutil.rmtree`` cleared non-mapped dirs). Categories keep the
    sidebar navigable instead of a 70-doc flat dump.
    """
    copied = 0

    def _emit(src: Path, dest_dir: str, dest_name: str, top_level: bool = True) -> None:
        nonlocal copied
        d = TARGET_DIR / dest_dir
        d.mkdir(parents=True, exist_ok=True)
        content = _fix_links(
            src.read_text(encoding="utf-8"), len(dest_dir.split("/")), allow_dot_prefix=top_level
        )
        (d / dest_name).write_text(content, encoding="utf-8")
        copied += 1

    # 1) Evaluations: NN-eval-*.md / NN-*-eval*.md at top level
    for f in sorted(SOURCE_DIR.glob("*.md"), key=lambda p: p.name.lower()):
        if f.name in DOC_MAPPING:
            continue
        if _is_eval_doc(f.name):
            _emit(f, "evaluations", f.name)

    # 2) ADRs — keep the subdir structure under adr/ (./x.md links stay siblings)
    adr_dir = SOURCE_DIR / "adr"
    if adr_dir.exists():
        for f in sorted(adr_dir.rglob("*.md"), key=lambda p: p.name.lower()):
            rel = f.relative_to(adr_dir)
            _emit(
                f,
                f"adr/{rel.parent}" if str(rel.parent) != "." else "adr",
                f.name,
                top_level=False,
            )

    # 3) Runbooks — same subtree passthrough
    rb_dir = SOURCE_DIR / "runbooks"
    if rb_dir.exists():
        for f in sorted(rb_dir.rglob("*.md"), key=lambda p: p.name.lower()):
            rel = f.relative_to(rb_dir)
            _emit(
                f,
                f"runbooks/{rel.parent}" if str(rel.parent) != "." else "runbooks",
                f.name,
                top_level=False,
            )

    # 4) Everything else top-level → resources/
    for f in sorted(SOURCE_DIR.glob("*.md"), key=lambda p: p.name.lower()):
        if f.name in DOC_MAPPING:
            continue
        if _is_eval_doc(f.name):
            continue
        _emit(f, "resources", f.name)

    print(f"  +{copied} extra docs published (evaluations/adr/runbooks/resources)")
    return copied


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
        # Depth = directories between site docs root and the emitted file:
        # intro.md lands at root (0), getting_started/intro.md lands at 1.
        depth = len(target_file.relative_to(TARGET_DIR).parts) - 1
        content = _fix_links(content, depth)
        target_file.write_text(content, encoding="utf-8")
        try:
            shown = target_file.relative_to(REPO_ROOT)
        except ValueError:
            shown = target_file  # scratch target (tests)
        print(f"  COPIED: {source_name} -> {shown}")
        copied += 1

    # Publish the rest of the corpus (evaluations, ADRs, runbooks, misc).
    sync_extra_docs()

    # Create _category_.json for each subdirectory
    categories = {
        "getting_started": ("Getting Started", 1),
        "architecture": ("Architecture", 2),
        "integrations": ("Integrations", 3),
        "operations": ("Operations", 4),
        "testing": ("Testing", 5),
        "project": ("Project Management", 6),
        "GLOSSARY": ("Glossary", 7),
        "evaluations": ("Evaluations", 8),
        "adr": ("ADRs", 9),
        "runbooks": ("Runbooks", 10),
        "resources": ("Resources", 11),
    }
    import json

    for dirname, (label, position) in categories.items():
        cat_dir = TARGET_DIR / dirname
        if not cat_dir.exists():
            continue
        # Curated sections stay expanded (existing behaviour); the new
        # high-volume categories (evaluations ~30 docs) start collapsed.
        collapsed = dirname in ("evaluations", "adr", "runbooks", "resources")
        cat_file = cat_dir / "_category_.json"
        cat_file.write_text(
            json.dumps({"label": label, "position": position, "collapsed": collapsed}),
            encoding="utf-8",
        )

    try:
        shown_target = TARGET_DIR.relative_to(REPO_ROOT)
    except ValueError:
        shown_target = TARGET_DIR
    print(f"\nSynced {copied} curated + extra documents to {shown_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync_docs())
