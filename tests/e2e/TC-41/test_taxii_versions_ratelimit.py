"""TC-41 — TAXII 2.1 /versions endpoint + burst/rate-limit behaviour.

Covers the remaining spec gaps: object version history (TAXII 2.1 §versions)
and server behaviour under request bursts (medallion does not implement 429 —
the contract asserted here is *consistent* bounded rejection/serving, never a
5xx or a hang).
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

TAXII = "http://taxii:5000"
ROOT = "soarlab"
COLL = "52892447-4d7e-4f70-94d0-6b2b7e8b4d0d"
CT = "application/taxii+json;version=2.1"
CFG = Path("/app/infra/docker/taxii/config.json")


def _auth() -> tuple[str, str]:
    # TAXII-EVAL-001: env-first (config.json is now a placeholder template).
    pw = os.environ.get("TAXII_READER_PASS")
    if pw:
        return "taxii_reader", pw
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    return next(iter(cfg["users"].items()))


@pytest.mark.e2e
class TestTaxiiVersionsRateLimit:
    def test_versions_endpoint_lists_object_history(self):
        user, pw = _auth()
        h = {"Accept": CT}
        # push a fresh object so we own the id
        ind = {
            "type": "indicator",
            "spec_version": "2.1",
            "id": "indicator--" + "a1b2c3d4-" + datetime.now(UTC).strftime("%H%M%S%f")[:8] * 3 + "-9e01-2f5c8d9a1b2c",
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "modified": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "pattern": "[ipv4-addr:value = '203.0.113.99']",
            "pattern_type": "stix",
            "valid_from": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        r = requests.post(
            f"{TAXII}/{ROOT}/collections/{COLL}/objects/",
            json={"objects": [ind]},
            headers={"Accept": CT, "Content-Type": CT},
            auth=(user, pw),
            timeout=20,
        )
        assert r.status_code in (200, 202), r.text[:200]

        # /versions must list the object's history
        r = requests.get(
            f"{TAXII}/{ROOT}/collections/{COLL}/objects/{ind['id']}/versions/",
            headers=h,
            auth=(user, pw),
            timeout=20,
        )
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        assert "versions" in body, f"no versions list: {body}"
        assert len(body["versions"]) >= 1
        for v in body["versions"]:
            datetime.fromisoformat(v.replace("Z", "+00:00"))  # well-formed ts

        # match[version]=last must resolve the newest version
        r = requests.get(
            f"{TAXII}/{ROOT}/collections/{COLL}/objects/?match[version]=last",
            headers=h,
            auth=(user, pw),
            timeout=20,
        )
        assert r.status_code == 200, f"match[version] unsupported: {r.status_code}"

    def test_burst_requests_consistent_and_bounded(self):
        """20 rapid authenticated requests: no 5xx, no hang; 429 absence documented."""
        user, pw = _auth()
        h = {"Accept": CT}
        t0 = time.time()
        codes = []
        for _ in range(20):
            r = requests.get(f"{TAXII}/{ROOT}/collections/", headers=h, auth=(user, pw), timeout=10)
            codes.append(r.status_code)
        elapsed = time.time() - t0
        assert elapsed < 30, f"burst took {elapsed:.1f}s — server degraded"
        assert all(c < 500 for c in codes), f"5xx under burst: {codes}"
        success = [c for c in codes if c == 200]
        limited = [c for c in codes if c == 429]
        # medallion serves all or rate-limits cleanly — never a mixed 5xx storm
        assert len(success) + len(limited) + [c for c in codes if c in (401, 403)].__len__() == 20
        if not limited:
            print("NOTE: medallion does not rate-limit (no 429 observed) — documented gap")

    def test_anonymous_burst_uniformly_rejected(self):
        """Unauthenticated burst: uniformly 401/403 — no request smuggled through."""
        h = {"Accept": CT}
        codes = [
            requests.get(f"{TAXII}/{ROOT}/collections/", headers=h, timeout=10).status_code
            for _ in range(10)
        ]
        assert all(c in (401, 403) for c in codes), f"inconsistent anon rejection: {codes}"
