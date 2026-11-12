#!/usr/bin/env python3
"""Proactive disk / flood-stage guardrail for the SOAR stack.

Checks, inside the Docker network:

1. ``_cat/allocation`` ``disk.percent`` for Elasticsearch AND OpenSearch
   (they share the same Docker Desktop disk — both must be checked).
2. OpenSearch ``_cluster/state/blocks`` for ``read_only_allow_delete``
   index blocks — the actual flood-stage condition that broke Shuffle
   auth lookups (401s) and e2e suites.

Exit codes: 0 healthy / 1 critical. ``--warn-only`` prints findings but
always exits 0 (used by ``make test-e2e`` so a high-but-safe disk informs
without aborting a 40-suite run).

    docker exec soar_api python3 /app/scripts/maintenance/check_disk_watermarks.py
    docker exec soar_api python3 /app/scripts/maintenance/check_disk_watermarks.py --warn-only
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.request

WARN_PCT = 88.0
CRIT_PCT = 95.0

ES_URL = os.environ.get("ELASTICSEARCH_URL", "https://elasticsearch:9200")
OS_URL = os.environ.get("SHUFFLE_OPENSEARCH_URL", "https://opensearch:9200")
_OS_AUTH = (
    "Basic "
    + base64.b64encode(
        f"{os.environ.get('SHUFFLE_OPENSEARCH_USERNAME', os.environ.get('OPENSEARCH_USERNAME', 'admin'))}:"
        f"{os.environ.get('SHUFFLE_OPENSEARCH_PASSWORD', os.environ.get('OPENSEARCH_PASSWORD', ''))}".encode()
    ).decode()
)
_ES_AUTH = (
    "Basic "
    + base64.b64encode(
        f"{os.environ.get('ELASTIC_USERNAME', 'elastic')}:"
        f"{os.environ.get('ELASTIC_PASSWORD', '')}".encode()
    ).decode()
)
_SSL_CTX = ssl.create_default_context(
    cafile="/app/certs/ca.crt" if os.path.exists("/app/certs/ca.crt") else None
)


def _get_json(url: str, timeout: int = 10, auth: str | None = None) -> object:
    headers = {"Accept": "application/json"}
    if auth:
        headers["Authorization"] = auth
    req = urllib.request.Request(url, headers=headers)
    ctx = _SSL_CTX if url.startswith("https") else None
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read())


def check_allocation(name: str, base_url: str, auth: str | None = None) -> list[dict]:
    """Return per-node disk usage for one search backend."""
    try:
        nodes = _get_json(f"{base_url}/_cat/allocation?v&format=json", auth=auth)
    except Exception as exc:  # noqa: BLE001
        return [{"backend": name, "node": "?", "disk_pct": -1.0, "error": str(exc)[:120]}]
    out = []
    for n in nodes or []:
        try:
            pct = float(n.get("disk.percent") or 0)
        except (TypeError, ValueError):
            pct = -1.0
        out.append(
            {
                "backend": name,
                "node": n.get("node", "?"),
                "disk_pct": pct,
                "disk_total": n.get("disk.total"),
                "disk_used": n.get("disk.used"),
            }
        )
    return out


def check_read_only_blocks(base_url: str, auth: str | None = None) -> list[str]:
    """Index names currently under ``read_only_allow_delete`` (flood-stage)."""
    try:
        state = _get_json(f"{base_url}/_cluster/state/blocks", auth=auth)
    except Exception:
        return []
    blocks = (state or {}).get("blocks", {}).get("indices", {})
    return sorted(blocks.keys())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args()

    nodes = check_allocation("elasticsearch", ES_URL, _ES_AUTH) + check_allocation(
        "opensearch", OS_URL, _OS_AUTH
    )
    ro_indices = check_read_only_blocks(OS_URL, _OS_AUTH)

    critical = False
    print("Disk watermarks (search backends share the Docker disk):")
    for n in nodes:
        pct = n["disk_pct"]
        if pct < 0:
            print(f"  {n['backend']:<14} {n['node']:<20} ERROR: {n.get('error', '?')}")
            critical = True  # unreachable search backend is itself critical
            continue
        level = "OK"
        if pct >= CRIT_PCT:
            level, critical = "CRITICAL", True
        elif pct >= WARN_PCT:
            level = "WARN"
        print(f"  {n['backend']:<14} {n['node']:<20} {pct:>5.1f}%  {level}")

    if ro_indices:
        critical = True
        print(f"\nFLOOD-STAGE ACTIVE — read_only_allow_delete on {len(ro_indices)} indices:")
        for idx in ro_indices[:10]:
            print(f"  - {idx}")
        print(
            "\nMitigation: docker container prune -f && docker builder prune -f "
            "(frees the shared disk; indices unblock automatically)"
        )
    elif critical:
        print(
            "\nAction recommended before heavy workloads: "
            "docker container prune -f && docker builder prune -f"
        )

    if critical and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
