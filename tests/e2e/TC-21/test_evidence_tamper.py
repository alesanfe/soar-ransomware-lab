#!/usr/bin/env python3
"""TC-21 ext: ACTIVE evidence tampering — field mutation, partial
rollback and deletion on REAL pipeline evidence (soar-metrics) must be
detectable via the production content fingerprint and count gaps."""

import os
import time

import pytest
import requests

from soar_lab.application.use_cases.alert_admission import (
    _content_fingerprint)
from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.forensic]

ES = "https://elasticsearch:9200"
ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))
METRICS = f"{ES}/soar-metrics"
ALERTS = f"{ES}/soar-alerts"


class TestEvidenceTamper(E2EBaseTest):
    tc_id = "TC-21"

    def _latest_metric(self) -> dict:
        r = requests.post(
            f"{METRICS}/_search",
            json={"size": 1, "sort": [{"timestamp": "desc"}]},
            auth=ES_AUTH, timeout=15)
        hits = r.json()["hits"]["hits"]
        assert hits, "no soar-metrics evidence docs"
        return hits[0]

    def _fp(self, src: dict) -> str:
        return _content_fingerprint(
            {k: v for k, v in src.items() if not k.startswith("@")})

    def _upd(self, doc_id: str, fields: dict) -> None:
        requests.post(f"{METRICS}/_update/{doc_id}?refresh=true",
                      json={"doc": fields}, auth=ES_AUTH, timeout=15)

    def test_fingerprint_detects_field_mutation(self):
        """Flipping `severity`/`decision` in a real evidence doc changes
        the recomputed fingerprint — tamper is detectable on re-verify.
        Original values are restored in teardown semantics (same pass)."""
        hit = self._latest_metric()
        src, doc_id = hit["_source"], hit["_id"]
        fp_before = self._fp(src)
        self._upd(doc_id, {"severity": 99, "decision": "tampered"})
        r = requests.get(f"{METRICS}/_doc/{doc_id}", auth=ES_AUTH, timeout=15)
        fp_after = self._fp(r.json()["_source"])
        try:
            assert fp_before != fp_after, (
                "mutation invisible to fingerprint — tamper undetectable"
            )
        finally:
            self._upd(doc_id, {
                "severity": src.get("severity"),
                "decision": src.get("decision"),
            })

    def test_fingerprint_detects_partial_rollback(self):
        """Mutate two fields, restore only one — the fingerprint still
        differs from the original: partial rollback is caught."""
        hit = self._latest_metric()
        src, doc_id = hit["_source"], hit["_id"]
        fp_orig = self._fp(src)
        self._upd(doc_id, {"severity": 99, "decision": "x"})
        self._upd(doc_id, {"severity": src.get("severity")})
        r = requests.get(f"{METRICS}/_doc/{doc_id}", auth=ES_AUTH, timeout=15)
        fp_partial = self._fp(r.json()["_source"])
        try:
            assert fp_partial != fp_orig, (
                "partial rollback indistinguishable from original"
            )
        finally:
            self._upd(doc_id, {"decision": src.get("decision")})

    def test_deleted_evidence_detectable_by_gap(self):
        """A deleted doc shows up as a count gap — silent deletion of
        evidence is detectable by reconciliation."""
        fid = f"tc21-evid-{int(time.time())}"
        w = requests.post(
            f"{ALERTS}/_doc/{fid}?refresh=true",
            json={"alert_id": fid, "source": "tc21", "severity": 2,
                  "status": "new", "timestamp": "2026-01-01T00:00:00Z"},
            auth=ES_AUTH, timeout=15)
        assert w.status_code in (200, 201), w.text[:200]
        try:
            def _count() -> int:
                return requests.post(
                    f"{ALERTS}/_count",
                    json={"query": {"ids": {"values": [fid]}}}, auth=ES_AUTH, timeout=15,
                ).json()["count"]

            before = 0
            for _ in range(10):
                before = _count()
                if before == 1:
                    break
                time.sleep(1)
            requests.delete(f"{ALERTS}/_doc/{fid}?refresh=true", auth=ES_AUTH, timeout=15)
            after = _count()
            assert before == 1 and after == 0, (
                f"deletion produced no detectable gap: {before}->{after}"
            )
        finally:
            requests.delete(f"{ALERTS}/_doc/{fid}", auth=ES_AUTH, timeout=10)
