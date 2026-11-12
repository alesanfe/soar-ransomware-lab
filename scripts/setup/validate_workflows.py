#!/usr/bin/env python3
"""Validate a generated Shuffle workflow definition (H-01).

Fetches the live workflow from the Shuffle API and checks:

  1. **Orphan nodes** — every action must be reachable from the start node
     via branches.
  2. **Dangling branches** — every branch source/destination must reference
     an existing action/trigger.
  3. **Unresolved variable refs** — every ``$name`` referenced in action
     parameters/scripts must resolve to a real action label (or an exec
     field ``$exec.*``).
  4. **Analyzer↔observable conformance** — every ``cortex_*`` node must bind
     an observable field the analyzer is compatible with per
     ``analyzer_matrix`` (catches the TC-KPI-06 file/hash miswiring class).
  5. **Guarded dispatch** — Cortex calls must go through the guarded
     python action, never a raw http action (regression check).

Exit code: 0 ok / 1 warnings only / 2 errors.

Run inside ``soar_api``::

    docker exec soar_api python3 /app/scripts/setup/validate_workflows.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/shuffle_workflow")
try:
    from shuffle_workflow.analyzer_matrix import (
        OBSERVABLE_FIELDS,
        allowed_fields,
        base_name,
    )
except ImportError:  # flat layout inside container (/app/scripts/setup/...)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shuffle_workflow"))
    from analyzer_matrix import OBSERVABLE_FIELDS, allowed_fields, base_name

SHUFFLE_URL = os.environ.get("SHUFFLE_BACKEND_URL", "https://shuffle-backend:5443")
WORKFLOW_NAME = os.environ.get("SOAR_WORKFLOW_NAME", "SOAR-Ransomware-Response")
REF_RE = re.compile(r"\$([a-zA-Z0-9_.]+)")
RESERVED_PREFIXES = ("exec.", "node.", "shuffle_var.")
RESERVED_WORDS = {"exec", "node", "shuffle_var"}


def _get(url: str, apikey: str) -> Any:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {apikey}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_workflow(apikey: str) -> dict[str, Any]:
    workflows = _get(f"{SHUFFLE_URL}/api/v1/workflows", apikey)
    for w in workflows:
        if w.get("name") == WORKFLOW_NAME:
            full = _get(f"{SHUFFLE_URL}/api/v1/workflows/{w['id']}", apikey)
            return full
    raise SystemExit(f"workflow '{WORKFLOW_NAME}' not found")


def validate(wf: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    actions = wf.get("actions") or []
    branches = wf.get("branches") or []
    triggers = wf.get("triggers") or []
    labels = {a.get("label") or a.get("name") for a in actions}
    ids = {a.get("id") for a in actions} | {t.get("id") for t in triggers}
    id_to_label = {a.get("id"): (a.get("label") or a.get("name")) for a in actions}

    # ── 1. Reachability from start ───────────────────────────────────
    start_id = wf.get("start") or (triggers[0].get("id") if triggers else None)
    adjacency: dict[str, list[str]] = {}
    for b in branches:
        src, dst = b.get("source_id"), b.get("destination_id")
        adjacency.setdefault(src, []).append(dst)
        # ── 2. dangling endpoints ──
        for ep, kind in ((src, "source"), (dst, "destination")):
            if ep not in ids:
                errors.append(f"branch {b.get('id','?')}: {kind} id {ep} not in workflow")
    reachable: set[str] = set()
    frontier = [start_id] if start_id else []
    while frontier:
        node = frontier.pop()
        if node in reachable or node is None:
            continue
        reachable.add(node)
        frontier.extend(adjacency.get(node, []))
    for a in actions:
        if a.get("id") not in reachable:
            warnings.append(f"orphan action: {a.get('label') or a.get('name')} ({a.get('id')})")

    for a in actions:
        label = a.get("label") or a.get("name") or "?"
        app = (a.get("app_name") or a.get("appName") or "").lower()
        # strip python comment lines so prose like "substitutes $var" is
        # ignored — Shuffle stores embedded code inside parameters too
        def _no_comments(text: str) -> str:
            return "\n".join(
                ln for ln in text.splitlines() if not ln.strip().startswith("#")
            )

        param_parts = []
        for prm in a.get("parameters") or []:
            v = prm.get("value") if isinstance(prm, dict) else prm
            param_parts.append(v if isinstance(v, str) else json.dumps(v))
        blob = "\n".join(
            _no_comments(p) for p in param_parts
        ) + _no_comments(a.get("code") or "")

        # ── 3. variable refs ──
        for ref in set(REF_RE.findall(blob)):
            if ref in RESERVED_WORDS or ref.startswith(RESERVED_PREFIXES):
                continue
            if ref.split(".")[0] not in labels:
                warnings.append(f"{label}: references missing variable ${ref}")

        # ── 4/5. cortex conformance ──
        lname = str(label).lower()
        if "cortex" in lname:
            code = a.get("code") or ""
            if "http" in app and "python" not in app:
                errors.append(f"{label}: raw http cortex call (must use guarded python)")
            # extract analyzer + field token from guarded code
            m_name = re.search(r'ANALYZER_NAME = "([^"]+)"', code)
            m_field = re.search(r'data = r"""\$exec\.([a-z_]+)"""', code)
            if m_name and m_field:
                aname, field_name = m_name.group(1), m_field.group(1)
                dyn = aname.replace("cortex_dyn_", "")
                field_key = {"src_ip": "ip"}.get(field_name, field_name)
                if field_key not in OBSERVABLE_FIELDS:
                    errors.append(f"{label}: field $exec.{field_name} is not a declared observable")
                else:
                    # conformance: analyzer must allow this field
                    compat = allowed_fields(aname, [])
                    if compat and field_key not in compat and dyn:
                        warnings.append(
                            f"{label}: analyzer {aname} bound to {field_key} "
                            f"outside matrix ({compat})"
                        )
                    if base_name(aname) in {"Virusshare"}:
                        errors.append(f"{label}: forbidden analyzer wired: {aname}")

    # required nodes sanity
    for required in ("normalize_inputs", "thehive_create_case", "es_index_metrics"):
        if required not in labels:
            errors.append(f"required node missing: {required}")

    return errors, warnings


def main() -> int:
    apikey = os.environ.get("SHUFFLE_DEFAULT_APIKEY", "")
    if not apikey:
        print("SHUFFLE_DEFAULT_APIKEY not set", file=sys.stderr)
        return 2
    wf = fetch_workflow(apikey)
    print(f"[validate] workflow '{wf.get('name')}' id={wf.get('id')} "
          f"actions={len(wf.get('actions') or [])} branches={len(wf.get('branches') or [])}")
    errors, warnings = validate(wf)
    for e in errors:
        print(f"  ERROR   {e}")
    for w in warnings:
        print(f"  WARN    {w}")
    print(f"[validate] {len(errors)} error(s), {len(warnings)} warning(s)")
    return 2 if errors else (1 if warnings else 0)


if __name__ == "__main__":
    sys.exit(main())
