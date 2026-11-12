#!/usr/bin/env python3
"""Provision OpenSearch + OpenSearch Dashboards for the SOAR lab.

Idempotent — safe to run repeatedly (OSD-003/004/005/008).

  * Index template ``shuffle-workflowexecution`` for ``workflowexecution-*``
    with ``started_at``/``completed_at`` mapped as ``date``
    (``epoch_second`` first — Shuffle stores epoch *seconds*, the default
    ``epoch_millis`` mapping silently lands every doc in 1970).
  * If the live ``workflowexecution-*`` backing index predates the fix,
    reindex it into a correctly mapped index and atomically re-point the
    ``workflowexecution`` alias (OSD-005).
  * Index patterns + a "SOAR – Shuffle Executions" dashboard in
    OpenSearch Dashboards via the saved_objects API (OSD-003/008).

Run inside ``soar_api``::

    docker exec soar_api python /app/scripts/setup/init_opensearch.py

or from the host with ``OPENSEARCH_URL``/``OPENSEARCH_DASHBOARDS_URL``
pointing at the published ports.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

from soar_lab.security.tls_config import ca_verify

OS_URL = os.environ.get("OPENSEARCH_URL", "https://opensearch:9200").rstrip("/")
OSD_URL = os.environ.get("OPENSEARCH_DASHBOARDS_URL", "http://opensearch-dashboards:5601").rstrip(
    "/"
)
OS_USER = os.environ.get("OPENSEARCH_USERNAME", "admin")
OS_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", "")

_verify = ca_verify()
if isinstance(_verify, str):
    _SSL_CTX = ssl.create_default_context(cafile=_verify)
elif _verify:
    _SSL_CTX = ssl.create_default_context()
else:
    _SSL_CTX = ssl._create_unverified_context()

_AUTH_HEADER = (
    "Basic " + base64.b64encode(f"{OS_USER}:{OS_PASSWORD}".encode()).decode()
    if OS_USER and OS_PASSWORD
    else None
)

EXEC_ALIAS = "workflowexecution"
EXEC_PATTERN = "workflowexecution*"
EXEC_BACKING_PREFIX = "workflowexecution-"

TEMPLATE = {
    "index_patterns": ["workflowexecution-*"],
    "priority": 200,
    "template": {
        "mappings": {
            "properties": {
                "started_at": {
                    "type": "date",
                    "format": "epoch_second||strict_date_optional_time||epoch_millis",
                },
                "completed_at": {
                    "type": "date",
                    "format": "epoch_second||strict_date_optional_time||epoch_millis",
                },
                "workflow": {
                    "properties": {
                        "name": {"type": "keyword"},
                        "id": {"type": "keyword"},
                    }
                },
            }
        }
    },
}

# -------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------


def _req(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    if _AUTH_HEADER:
        req.add_header("Authorization", _AUTH_HEADER)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw.decode(errors="replace")[:500]}
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}


def wait_for(url: str, path: str, name: str, tries: int = 30) -> None:
    for i in range(tries):
        code, _ = _req(url + path, timeout=5)
        if code == 200:
            print(f"[OK] {name} reachable")
            return
        time.sleep(2)
    raise SystemExit(f"[FAIL] {name} not reachable at {url}{path}")


# -------------------------------------------------------------------
# OpenSearch side
# -------------------------------------------------------------------


def ensure_template() -> None:
    code, _ = _req(
        f"{OS_URL}/_index_template/shuffle-workflowexecution",
        method="PUT",
        body=TEMPLATE,
    )
    if code in (200, 201):
        print("[OK] index template shuffle-workflowexecution applied")
    else:
        print(f"[WARN] template PUT -> {code}")


def _mapping_format(index: str) -> str | None:
    code, m = _req(f"{OS_URL}/{index}/_mapping/field/started_at")
    if code != 200:
        return None
    try:
        field = m[index]["mappings"]["started_at"]["mapping"]["started_at"]
        return field.get("format", "")
    except (KeyError, TypeError):
        return None


def _min_epoch_year(index: str) -> int | None:
    code, r = _req(
        f"{OS_URL}/{index}/_search",
        method="POST",
        body={"size": 0, "aggs": {"y": {"min": {"field": "started_at"}}}},
    )
    if code != 200:
        return None
    ms = r.get("aggregations", {}).get("y", {}).get("value")
    if ms is None:
        return None
    return int(ms // 1000 // 31556952 + 1970)


def fix_epoch_seconds_index() -> None:
    """Reindex the live executions index if its dates are in 1970."""
    code, aliases = _req(f"{OS_URL}/_alias/{EXEC_ALIAS}")
    if code != 200:
        print(f"[WARN] alias {EXEC_ALIAS} -> {code}, skipping reindex")
        return
    backing = [i for i in aliases if i.startswith(EXEC_BACKING_PREFIX)]
    if not backing:
        print("[WARN] no backing index for alias")
        return
    src = max(backing)

    fmt = _mapping_format(src)
    year = _min_epoch_year(src)
    print(f"[INFO] backing={src} format={fmt!r} min_year={year}")
    if fmt and "epoch_second" in fmt and (year is None or year > 2000):
        print("[OK] executions index already epoch_second-mapped, no reindex")
        return

    # next index number
    suffixes = [int(i.rsplit("-", 1)[-1]) for i in backing if i.rsplit("-", 1)[-1].isdigit()]
    dst = f"{EXEC_BACKING_PREFIX}{max(suffixes or [0]) + 1:06d}"

    # Manual scroll+bulk reindex — a single _reindex request exceeds the
    # coordinating-bytes limit (execution docs carry large `result` bodies).
    created = 0
    code, page = _req(
        f"{OS_URL}/{src}/_search?scroll=2m",
        method="POST",
        body={"size": 25, "sort": ["_doc"], "query": {"match_all": {}}},
        timeout=60,
    )
    while code == 200:
        hits = page.get("hits", {}).get("hits", [])
        if not hits:
            break
        ndjson = "".join(
            '{"index":{"_index":"%s","_id":"%s"}}\n%s\n' % (dst, h["_id"], json.dumps(h["_source"]))
            for h in hits
        )
        bulk_headers = {"Content-Type": "application/x-ndjson"}
        if _AUTH_HEADER:
            bulk_headers["Authorization"] = _AUTH_HEADER
        req = urllib.request.Request(
            f"{OS_URL}/_bulk?refresh=false",
            data=ndjson.encode(),
            headers=bulk_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as r:
                bulk = json.loads(r.read())
            if bulk.get("errors"):
                print(f"[FAIL] bulk errors: {str(bulk)[:300]}")
                return
            created += len(hits)
        except urllib.error.HTTPError as e:
            print(f"[FAIL] bulk -> {e.code} {e.read()[:200]}")
            return
        code, page = _req(
            f"{OS_URL}/_search/scroll",
            method="POST",
            body={"scroll": "2m", "scroll_id": page["_scroll_id"]},
            timeout=60,
        )
    print(f"[INFO] copied {created} docs to {dst}")

    _req(f"{OS_URL}/{dst}/_refresh", method="POST")
    code, cnt = _req(f"{OS_URL}/{dst}/_count")
    if code != 200 or cnt.get("count", 0) < created:
        print(f"[FAIL] dest count mismatch: created={created} dest={cnt}")
        return

    # atomic alias swap; keep the old index around (do not delete)
    code, _ = _req(
        f"{OS_URL}/_aliases",
        method="POST",
        body={
            "actions": [
                {"remove": {"index": src, "alias": EXEC_ALIAS}},
                {"add": {"index": dst, "alias": EXEC_ALIAS}},
            ]
        },
    )
    if code == 200:
        print(
            f"[OK] reindexed {src} -> {dst} ({created} docs), "
            f"alias {EXEC_ALIAS} swapped (old index kept)"
        )
    else:
        print(f"[FAIL] alias swap -> {code}")


# -------------------------------------------------------------------
# Dashboards side
# -------------------------------------------------------------------

OSD_HEADERS = {"osd-xsrf": "true"}


def osd_saved(obj_type: str, obj_id: str, attributes: dict, references: list) -> None:
    code, r = _req(
        f"{OSD_URL}/api/saved_objects/{obj_type}/{obj_id}?overwrite=true",
        method="POST",
        body={"attributes": attributes, "references": references},
        headers=OSD_HEADERS,
    )
    if code in (200, 201):
        print(f"[OK] {obj_type}/{obj_id}")
    else:
        print(f"[WARN] {obj_type}/{obj_id} -> {code} {str(r)[:200]}")


def ensure_index_patterns() -> None:
    for pid, title, tf in (
        ("ip_workflowexecution", "workflowexecution*", "started_at"),
        ("ip_shuffle_logs", "shuffle_logs*", None),
    ):
        attrs: dict = {"title": title}
        if tf:
            attrs["timeFieldName"] = tf
        osd_saved("index-pattern", pid, attrs, [])


def _vis(vis_id: str, title: str, vis_type: str, aggs: list, params: dict) -> None:
    vis_state = {
        "title": title,
        "type": vis_type,
        "params": params,
        "aggs": aggs,
    }
    search_source = {
        "index": "ip_workflowexecution",
        "query": {"query": "", "language": "kuery"},
        "filter": [],
    }
    osd_saved(
        "visualization",
        vis_id,
        {
            "title": title,
            "visState": json.dumps(vis_state),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(search_source)},
            "version": 1,
        },
        [
            {
                "id": "ip_workflowexecution",
                "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
                "type": "index-pattern",
            }
        ],
    )


def ensure_dashboard() -> None:
    _vis(
        "vis_exec_count",
        "Executions (total)",
        "metric",
        [{"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}}],
        {
            "addTooltip": True,
            "addLegend": False,
            "type": "metric",
            "metric": {
                "percentageMode": False,
                "useRanges": False,
                "colorSchema": "Green to Red",
                "metricColorMode": "None",
                "colorsRange": [{"from": 0, "to": 10000}],
                "invertColors": False,
                "labels": {"show": True},
                "collection": {"labelsColor": "rgb(0,0,0)"},
                "style": {
                    "bgFill": "#000",
                    "bgColor": False,
                    "labelColor": False,
                    "subText": "",
                    "fontSize": 60,
                },
            },
        },
    )
    _vis(
        "vis_exec_status",
        "Executions by status",
        "pie",
        [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {"field": "status", "size": 10, "order": "desc", "orderBy": "1"},
            },
        ],
        {
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "isDonut": True,
            "type": "pie",
            "labels": {"show": True, "values": True, "last_level": True, "truncate": 100},
        },
    )
    _vis(
        "vis_exec_time",
        "Executions over time",
        "line",
        [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {
                "id": "2",
                "enabled": True,
                "type": "date_histogram",
                "schema": "segment",
                "params": {
                    "field": "started_at",
                    "timeRange": {"from": "now-30d", "to": "now"},
                    "useNormalizedOpenSearchInterval": True,
                    "scaleMetricValues": False,
                    "interval": "auto",
                    "drop_partials": False,
                    "min_doc_count": 1,
                    "extended_bounds": {},
                },
            },
        ],
        {
            "type": "line",
            "grid": {"categoryLines": False},
            "categoryAxes": [
                {
                    "id": "CategoryAxis-1",
                    "type": "category",
                    "position": "bottom",
                    "show": True,
                    "scale": {"type": "linear"},
                    "labels": {"show": True, "filter": True, "truncate": 100},
                    "title": {},
                    "style": {},
                }
            ],
            "valueAxes": [
                {
                    "id": "ValueAxis-1",
                    "name": "LeftAxis-1",
                    "type": "value",
                    "position": "left",
                    "show": True,
                    "scale": {"type": "linear", "mode": "normal"},
                    "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                    "title": {"text": "Count"},
                    "style": {},
                }
            ],
            "seriesParams": [
                {
                    "show": True,
                    "type": "line",
                    "mode": "normal",
                    "data": {"label": "Count", "id": "1"},
                    "valueAxis": "ValueAxis-1",
                    "drawLinesBetweenPoints": True,
                    "lineWidth": 2,
                    "interpolate": "linear",
                    "showCircles": True,
                }
            ],
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False,
            "thresholdLine": {
                "show": False,
                "value": 10,
                "width": 1,
                "style": "full",
                "color": "#E7664C",
            },
            "labels": {},
        },
    )
    _vis(
        "vis_exec_workflow",
        "Executions by workflow",
        "table",
        [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "bucket",
                "params": {
                    "field": "workflow.name",
                    "size": 10,
                    "order": "desc",
                    "orderBy": "1",
                    "otherBucket": False,
                    "otherBucketLabel": "Other",
                    "missingBucket": False,
                    "missingBucketLabel": "Missing",
                },
            },
        ],
        {
            "type": "table",
            "perPage": 10,
            "showPartialRows": False,
            "showMetricsAtAllLevels": False,
            "sort": {"columnIndex": None, "direction": None},
            "showTotal": False,
            "totalFunc": "sum",
            "percentageCol": "",
        },
    )

    panels = [
        {
            "gridData": {"x": 0, "y": 0, "w": 12, "h": 8, "i": "1"},
            "version": "2.10.0",
            "panelIndex": "1",
            "type": "visualization",
            "id": "vis_exec_count",
            "panelRefName": "panel_0",
        },
        {
            "gridData": {"x": 12, "y": 0, "w": 12, "h": 8, "i": "2"},
            "version": "2.10.0",
            "panelIndex": "2",
            "type": "visualization",
            "id": "vis_exec_status",
            "panelRefName": "panel_1",
        },
        {
            "gridData": {"x": 0, "y": 8, "w": 12, "h": 10, "i": "3"},
            "version": "2.10.0",
            "panelIndex": "3",
            "type": "visualization",
            "id": "vis_exec_time",
            "panelRefName": "panel_2",
        },
        {
            "gridData": {"x": 12, "y": 8, "w": 12, "h": 10, "i": "4"},
            "version": "2.10.0",
            "panelIndex": "4",
            "type": "visualization",
            "id": "vis_exec_workflow",
            "panelRefName": "panel_3",
        },
    ]
    osd_saved(
        "dashboard",
        "dash_shuffle_executions",
        {
            "title": "SOAR - Shuffle Executions",
            "hits": 0,
            "description": "Provisioned by scripts/setup/init_opensearch.py (OSD-003)",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps(
                {"useMargins": True, "syncColors": False, "hidePanelTitles": False}
            ),
            "version": 1,
            "timeRestore": True,
            "timeTo": "now",
            "timeFrom": "now-30d",
            "refreshInterval": {"pause": False, "value": 30000},
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(
                    {"query": {"query": "", "language": "kuery"}, "filter": []}
                )
            },
        },
        [
            {"id": "vis_exec_count", "name": "panel_0", "type": "visualization"},
            {"id": "vis_exec_status", "name": "panel_1", "type": "visualization"},
            {"id": "vis_exec_time", "name": "panel_2", "type": "visualization"},
            {"id": "vis_exec_workflow", "name": "panel_3", "type": "visualization"},
        ],
    )


def main() -> int:
    print(f"[INFO] OpenSearch={OS_URL} Dashboards={OSD_URL}")
    wait_for(OS_URL, "/_cluster/health", "OpenSearch")
    wait_for(OSD_URL, "/api/status", "OpenSearch Dashboards", tries=60)

    ensure_template()
    fix_epoch_seconds_index()
    ensure_index_patterns()
    ensure_dashboard()
    print("[DONE] OpenSearch provisioning complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
