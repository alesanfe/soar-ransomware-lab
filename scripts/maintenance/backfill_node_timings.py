#!/usr/bin/env python3
"""Backfill per-node timings into ``soar-metrics`` workflow_execution docs.

``build_metrics_json.py`` runs *inside* the workflow, so it cannot see the
per-action ``started_at``/``completed_at`` that Shuffle stores in the
``workflowexecution`` index — it leaves ``node_timings`` and the four
component timings at zero/None. This script runs *after* executions finish
and patches the real values in.

For each recent FINISHED execution it:

  1. Extracts per-node timings via ``NodeTimingExtractor.extract_timings``.
  2. Locates the matching ``soar-metrics`` document (``_id == alert_id``,
     parsed out of ``execution_argument``).
  3. ``_update``s it with ``node_timings`` + the component timings derived
     from node spans:
       - ``reception_time_s``    = normalize_inputs span
       - ``analysis_time_s``     = cortex_*/misp_*/enrichment span
       - ``case_creation_time_s``= thehive_* span
       - ``containment_time_s``  = containment node duration

Idempotent: re-running overwrites the same fields with the same values.

Run inside the ``soar_api`` container::

    docker exec soar_api python3 /app/scripts/maintenance/backfill_node_timings.py \
        --size 200
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.request
from typing import Any

from soar_lab.application.use_cases.node_timing_extractor import NodeTimingExtractor
from soar_lab.security.tls_config import ca_verify

OPENSEARCH_URL = os.environ.get(
    "SHUFFLE_OPENSEARCH_URL", os.environ.get("OPENSEARCH_URL", "https://opensearch:9200")
)
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "https://elasticsearch:9200")
EXECUTION_INDEX = os.environ.get("SHUFFLE_EXECUTION_INDEX", "workflowexecution")
METRICS_INDEX = os.environ.get("SOAR_METRICS_INDEX", "soar-metrics")

OS_AUTH = (
    os.environ.get(
        "SHUFFLE_OPENSEARCH_USERNAME", os.environ.get("OPENSEARCH_USERNAME", "admin")
    ),
    os.environ.get(
        "SHUFFLE_OPENSEARCH_PASSWORD", os.environ.get("OPENSEARCH_PASSWORD", "")
    ),
)
ES_AUTH = (
    os.environ.get("ELASTIC_USERNAME", "elastic"),
    os.environ.get("ELASTIC_PASSWORD", ""),
)

_verify = ca_verify()
if isinstance(_verify, str):
    _SSL_CTX = ssl.create_default_context(cafile=_verify)
elif _verify:
    _SSL_CTX = ssl.create_default_context()
else:
    _SSL_CTX = ssl._create_unverified_context()

_ANALYSIS_PREFIXES = (
    "cortex_",
    "misp_",
    "tenzir_",
    "network_watch",
    "redis_cache",
    "loki_search",
)
_CASE_PREFIXES = ("thehive_",)


def _post(
    url: str, payload: dict[str, Any], timeout: int = 30, auth: tuple[str, str] | None = None
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if auth and auth[1]:
        cred = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {cred}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
        return json.loads(r.read())


def _span(nodes: dict[str, dict[str, Any]], prefixes: tuple[str, ...]) -> float:
    """Wall-clock span (s) covering all nodes whose label starts with a prefix."""
    starts, ends = [], []
    for label, info in nodes.items():
        if not label.startswith(prefixes):
            continue
        off = info.get("start_offset_s")
        dur = info.get("duration_s")
        if off is None or dur is None:
            continue
        starts.append(off)
        ends.append(off + dur)
    return round(max(ends) - min(starts), 3) if starts else 0.0


def _node_duration(nodes: dict[str, dict[str, Any]], label: str) -> float:
    info = nodes.get(label)
    if not info:
        return 0.0
    return round((info.get("start_offset_s") or 0) + (info.get("duration_s") or 0), 3)


def _component_timings(nodes: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {
        "reception_time_s": _node_duration(nodes, "normalize_inputs"),
        "analysis_time_s": _span(nodes, _ANALYSIS_PREFIXES),
        "case_creation_time_s": _span(nodes, _CASE_PREFIXES),
        "containment_time_s": _node_duration(nodes, "containment"),
    }


def _to_doc_timings(nodes: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Convert extractor nodes → the soar-metrics ``node_timings`` shape.

    The report reads ``duration_s`` (fallback ``duration``) and ``status``;
    ``start_offset_s``/``occurrences`` are kept for bottleneck analysis.
    """
    out = {}
    for label, info in nodes.items():
        out[label] = {
            "start": None,
            "end": None,
            "duration": info.get("duration_s", 0),
            "duration_s": info.get("duration_s", 0),
            "start_offset_s": info.get("start_offset_s", 0),
            "status": info.get("status", "UNKNOWN"),
            "occurrences": info.get("occurrences", 1),
        }
    return out


def fetch_finished_executions(size: int) -> list[dict[str, Any]]:
    data = _post(
        f"{OPENSEARCH_URL.rstrip('/')}/{EXECUTION_INDEX}/_search",
        {
            "size": size,
            "sort": [{"started_at": {"order": "desc"}}],
            "query": {
                "bool": {
                    "should": [
                        {"term": {"status": "FINISHED"}},
                        {"term": {"status.keyword": "FINISHED"}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "_source": True,
        },
        auth=OS_AUTH,
    )
    return [h["_source"] for h in data.get("hits", {}).get("hits", [])]


def _alert_id_of(execution: dict[str, Any]) -> str:
    arg = execution.get("execution_argument") or ""
    if isinstance(arg, str):
        try:
            arg = json.loads(arg)
        except Exception:
            return ""
    return str(arg.get("alert_id") or "") if isinstance(arg, dict) else ""


def patch_metrics_doc(alert_id: str, doc_fields: dict[str, Any]) -> bool:
    data = _post(
        f"{ELASTICSEARCH_URL.rstrip('/')}/{METRICS_INDEX}/_update/{alert_id}",
        {"doc": doc_fields, "doc_as_upsert": False},
        auth=ES_AUTH,
    )
    return data.get("result") in ("updated", "noop")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=200, help="recent FINISHED executions to scan")
    ap.add_argument("--dry-run", action="store_true", help="compute but do not write")
    args = ap.parse_args()

    extractor = NodeTimingExtractor(
        opensearch_url=OPENSEARCH_URL,
        opensearch_user=OS_AUTH[0],
        opensearch_pass=OS_AUTH[1],
        elasticsearch_url=ELASTICSEARCH_URL,
        elasticsearch_user=ES_AUTH[0],
        elasticsearch_pass=ES_AUTH[1],
    )
    executions = fetch_finished_executions(args.size)
    print(f"[backfill] scanning {len(executions)} FINISHED execution(s)")

    patched = skipped = missing = 0
    for execution in executions:
        alert_id = _alert_id_of(execution)
        if not alert_id:
            skipped += 1
            continue
        timings = extractor.extract_timings(execution)
        nodes = timings.get("nodes", {})
        if not nodes:
            skipped += 1
            continue
        fields = {
            "node_timings": _to_doc_timings(nodes),
            "workflow_duration_s": timings.get("workflow_duration_s", 0),
            "execution_id": timings.get("execution_id", ""),
            **_component_timings(nodes),
        }
        if args.dry_run:
            patched += 1
            continue
        try:
            if patch_metrics_doc(alert_id, fields):
                patched += 1
            else:
                missing += 1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                missing += 1
            else:
                print(f"[backfill] {alert_id}: update failed: {e}")
                skipped += 1
        except Exception as e:
            print(f"[backfill] {alert_id}: update failed: {e}")
            skipped += 1

    print(
        f"[backfill] patched={patched} no-metrics-doc={missing} "
        f"skipped={skipped} (dry_run={args.dry_run})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
