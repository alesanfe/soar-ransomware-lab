"""Regenerate the live-data block of docs/16 (ISO 25040 audit ficha).

Refreshes only the rows wrapped in ``<!-- AUDIT-LIVE:BEGIN -->`` /
``<!-- AUDIT-LIVE:END -->`` markers inside the "Ficha de evaluación"
table — the audit prose, scores and findings are authored manually and
are never touched. Also emits a full machine-readable snapshot to
``reports/audit/audit_context.json`` so results cite the exact commit
and environment evaluated (DOC-01).

Usage:
    python scripts/reports/generate_audit_report.py          # update docs/16
    python scripts/reports/generate_audit_report.py --check  # exit 1 if stale
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOC16 = ROOT / "docs" / "16-formal-audit-iso25040.md"
SNAPSHOT = ROOT / "reports" / "audit" / "audit_context.json"

MARK_BEGIN = "<!-- AUDIT-LIVE:BEGIN -->"
MARK_END = "<!-- AUDIT-LIVE:END -->"


def _run(cmd: list[str], timeout: int = 30) -> str:
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def collect_context() -> dict:
    """Live audit context: commit, tree state, environment, evidence."""
    ctx: dict = {"generated_at": datetime.now(UTC).isoformat()}

    ctx["commit"] = _run(["git", "rev-parse", "HEAD"]) or "unknown"
    ctx["branch"] = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    dirty = _run(["git", "status", "--porcelain"])
    ctx["uncommitted_files"] = len(dirty.splitlines()) if dirty else 0
    ctx["python"] = sys.version.split()[0]
    ctx["docker"] = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    ctx["compose_running"] = len(
        [ln for ln in _run(["docker", "compose", "ps", "-q"]).splitlines() if ln.strip()]
    )

    evidence = {}
    for rel in (
        "reports/test-review/e2e_oracle_audit.json",
        "reports/test-review/test_review_summary.json",
        "reports/perf/soak-soak30.summary.json",
        "reports/audit/freeze.txt",
    ):
        p = ROOT / rel
        evidence[rel] = (
            datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat() if p.exists() else None
        )
    ctx["evidence_artifacts"] = evidence
    return ctx


def render_block(ctx: dict) -> str:
    """Markdown table rows for the live ficha fields."""
    date = ctx["generated_at"][:10]
    env = (
        f"Docker {ctx['docker'] or 'n/a'}, {ctx['compose_running']} contenedores, "
        f"perfil hardened por defecto (lab requiere `LAB=1`)"
    )
    return "\n".join(
        [
            MARK_BEGIN,
            f"| Commit | `{ctx['commit']}` |",
            f"| Estado del árbol | {ctx['uncommitted_files']} ficheros sin commitear "
            "(working tree como fuente de verdad — AGENTS.md) |",
            f"| Fecha | {date} |",
            f"| Entorno | {env} |",
            f"| Datos generados | `{ctx['generated_at']}` por `make audit-report` |",
            MARK_END,
        ]
    )


def update_doc(ctx: dict, check: bool = False) -> bool:
    """Refresh the AUDIT-LIVE block. Returns True when doc is up to date."""
    if not DOC16.exists():
        print(f"error: {DOC16} not found", file=sys.stderr)
        return False
    text = DOC16.read_text(encoding="utf-8")
    block = render_block(ctx)

    if MARK_BEGIN in text and MARK_END in text:
        pre, rest = text.split(MARK_BEGIN, 1)
        _, post = rest.split(MARK_END, 1)
        new_text = pre + block + post
    else:
        # First run: wrap the live rows of the ficha table (Commit → Entorno).
        lines = text.splitlines(keepends=True)
        start = next(
            (i for i, ln in enumerate(lines) if ln.startswith("| Commit |")), None
        )
        end = next(
            (i for i, ln in enumerate(lines) if ln.startswith("| Entorno |")), None
        )
        if start is None or end is None:
            print("error: ficha rows (| Commit | / | Entorno |) not found", file=sys.stderr)
            return False
        new_text = (
            "".join(lines[:start])
            + block
            + "\n"
            + "".join(lines[end + 1 :])
        )

    if check:
        return new_text == text
    if new_text != text:
        DOC16.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if docs/16 is stale")
    args = ap.parse_args()

    ctx = collect_context()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(ctx, indent=2) + "\n", encoding="utf-8")

    ok = update_doc(ctx, check=args.check)
    if args.check and not ok:
        print("docs/16 AUDIT-LIVE block is stale — run `make audit-report`")
        return 1
    print(f"audit context -> {SNAPSHOT}")
    print(f"docs/16 {'up to date' if ok else 'updated'} (commit {ctx['commit'][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
