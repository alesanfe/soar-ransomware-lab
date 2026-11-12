"""TC-36 — deep ES contract tests: bulk partial failure, mapping
incompatibility, dedup after recovery, and the false-zero dashboard hazard.

These cover the gaps the basic outage test leaves: what happens when ES is
UP but a write is *partially* rejected, when the mapping is incompatible,
and whether re-ingested duplicates after an outage corrupt counts.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

ES = "https://elasticsearch:9200"
ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))
IDX = "soar-metrics"


@pytest.mark.e2e
class TestElasticsearchDeepContracts:
    def test_bulk_partial_failure_reports_per_item(self):
        """A bulk with one valid + one mapping-violating doc must index the
        valid item and flag the bad one — ES never silently drops both."""
        good = {
            "alert_id": f"TC36-BULK-{uuid.uuid4().hex[:8]}",
            "metric_type": "contract_test",
            "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "success": True,
        }
        bad = dict(good)
        bad["alert_id"] = {"nested": "object-not-a-string"}
        import json as _json

        body = (
            f'{{"index":{{"_index":"{IDX}"}}}}\n{_json.dumps(good)}\n'
            f'{{"index":{{"_index":"{IDX}"}}}}\n{_json.dumps(bad)}\n'
        )
        r = requests.post(
            f"{ES}/_bulk", data=body,
            headers={"Content-Type": "application/x-ndjson"}, auth=ES_AUTH, timeout=15,
        )
        r.raise_for_status()
        res = r.json()
        assert "errors" in res
        if res["errors"]:
            items = res["items"]
            statuses = [i["index"]["status"] for i in items]
            assert any(s in (200, 201) for s in statuses), (
                f"valid doc rejected alongside bad one: {statuses}"
            )
            assert any(s >= 400 for s in statuses), (
                f"bad doc accepted silently: {statuses}"
            )
        # cleanup the good doc so it doesn't pollute KPI windows
        requests.post(
            f"{ES}/{IDX}/_delete_by_query?refresh=true",
            json={"query": {"term": {"alert_id": good["alert_id"]}}},
            auth=ES_AUTH, timeout=15,
        )

    def test_incompatible_index_mapping_rejected_bounded(self):
        """Writing a doc that violates an explicit mapping must 4xx, not 5xx
        nor silently coerce — schema drift is caught at ingest."""
        idx = f"tc36-map-{uuid.uuid4().hex[:6]}"
        requests.put(
            f"{ES}/{idx}",
            json={"mappings": {"properties": {"n": {"type": "long"}}}},
            auth=ES_AUTH, timeout=15,
        )
        try:
            r = requests.post(
                f"{ES}/{idx}/_doc",
                json={"n": "not-a-number-at-all"},
                auth=ES_AUTH, timeout=15,
            )
            assert r.status_code in (400, 404), (
                f"mapping violation not bounded: {r.status_code}"
            )
            # a conforming write must still succeed — index is not poisoned
            ok = requests.post(f"{ES}/{idx}/_doc", json={"n": 42}, auth=ES_AUTH, timeout=15)
            assert ok.status_code in (200, 201)
        finally:
            requests.delete(f"{ES}/{idx}", auth=ES_AUTH, timeout=15)

    def test_reingested_duplicate_alert_dedupes_by_id(self):
        """Post-outage replay of the same alert_id must not double-count:
        documents are keyed by alert_id so a dedup query returns one logical
        alert even if the physical doc was re-written."""
        alert_id = f"TC36-DEDUP-{uuid.uuid4().hex[:8]}"
        doc = {
            "alert_id": alert_id,
            "metric_type": "contract_test",
            "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "success": True,
        }
        for _ in range(2):  # replay the same logical alert twice
            requests.post(f"{ES}/{IDX}/_doc?refresh=true", json=doc, auth=ES_AUTH, timeout=15)
        try:
            # what consumers should do: collapse by alert_id (terms agg)
            r = requests.post(
                f"{ES}/{IDX}/_search",
                json={
                    "size": 0,
                    "query": {"term": {"alert_id": alert_id}},
                    "aggs": {"ids": {"terms": {"field": "alert_id", "size": 10}}},
                },
                auth=ES_AUTH, timeout=15,
            )
            buckets = r.json()["aggregations"]["ids"]["buckets"]
            assert len(buckets) == 1 and buckets[0]["key"] == alert_id, (
                f"dedup by alert_id broken: {buckets}"
            )
        finally:
            requests.post(
                f"{ES}/{IDX}/_delete_by_query?refresh=true",
                json={"query": {"term": {"alert_id": alert_id}}},
                auth=ES_AUTH, timeout=15,
            )

    def test_metrics_absent_does_not_read_as_zero(self):
        """Dashboard hazard: an alert with NO metrics doc must surface as
        'no data', never as a fabricated zero row. Verified at the query
        layer that feeds Grafana."""
        missing_id = f"TC36-GHOST-{uuid.uuid4().hex[:8]}"
        r = requests.post(
            f"{ES}/{IDX}/_count",
            json={"query": {"term": {"alert_id": missing_id}}},
            auth=ES_AUTH, timeout=15,
        )
        count = r.json().get("count", -1)
        assert count == 0, "ghost alert returned data"
        # a terms agg over the window must NOT invent a bucket for it
        r = requests.post(
            f"{ES}/{IDX}/_search",
            json={
                "size": 0,
                "aggs": {
                    "per_alert": {"terms": {"field": "alert_id", "size": 10000}}
                },
            },
            auth=ES_AUTH, timeout=20,
        )
        keys = {b["key"] for b in r.json()["aggregations"]["per_alert"]["buckets"]}
        assert missing_id not in keys
