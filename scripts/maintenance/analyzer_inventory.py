#!/usr/bin/env python3
"""Cortex analyzer inventory (A-04).

Lists every installed Cortex analyzer and classifies it against the
Observable→Analyzer matrix:

  - ``wired``          — compatible and wired in the generated workflow
  - ``compatible``     — could be wired (has a satisfiable observable)
  - ``file_only``      — requires a file artifact the webhook never carries
  - ``forbidden``      — in the skip list (missing keys/known-broken)
  - ``no_datatype``    — declares no dataType the payload can satisfy

Writes ``reports/validation/results/analyzer_inventory.json``.

Run inside ``soar_api``::

    docker exec soar_api python3 /app/scripts/maintenance/analyzer_inventory.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from typing import Any

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "setup", "shuffle_workflow"
    ),
)
try:
    from shuffle_workflow.analyzer_matrix import (
        FORBIDDEN_BASES,
        OBSERVABLE_FIELDS,
        allowed_fields,
        base_name,
    )
except ImportError:
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "setup",
            "shuffle_workflow",
        ),
    )
    from analyzer_matrix import (
        FORBIDDEN_BASES,
        OBSERVABLE_FIELDS,
        allowed_fields,
        base_name,
    )

CORTEX_URL = os.environ.get("CORTEX_URL", "https://cortex:9443")
OUT_PATH = "/app/reports/validation/results/analyzer_inventory.json"


def _get(path: str) -> Any:
    key = os.environ.get("CORTEX_API_KEY", "")
    req = urllib.request.Request(
        f"{CORTEX_URL}{path}", headers={"Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def classify(name: str, dtypes: list[str]) -> tuple[str, list[str]]:
    if base_name(name) in FORBIDDEN_BASES:
        return "forbidden", []
    compat = allowed_fields(name, dtypes)
    if compat:
        return "compatible", compat
    if dtypes and all(d == "file" for d in dtypes):
        return "file_only", []
    return "no_datatype", []


def main() -> int:
    try:
        analyzers = _get("/api/analyzer")
    except Exception as e:
        print(f"[inventory] cortex unreachable: {e}")
        return 1
    if not isinstance(analyzers, list):
        analyzers = []

    rows = []
    counts: dict[str, int] = {}
    for a in sorted(analyzers, key=lambda x: x.get("name", "")):
        name = a.get("name", "")
        dtypes = a.get("dataTypeList", []) or []
        cls, fields = classify(name, dtypes)
        counts[cls] = counts.get(cls, 0) + 1
        rows.append(
            {
                "name": name,
                "id": a.get("id") or a.get("_id", ""),
                "base": base_name(name),
                "dataTypeList": dtypes,
                "class": cls,
                "compatible_fields": fields,
                "enabled": a.get("enabled", a.get("isEnabled", True)),
            }
        )

    print(f"[inventory] {len(rows)} analyzers: {counts}")
    for r in rows:
        print(f"  {r['class']:12} {r['name']:50} -> {r['compatible_fields']}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"total": len(rows), "counts": counts, "analyzers": rows},
            f,
            indent=2,
        )
    print(f"[inventory] written {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
