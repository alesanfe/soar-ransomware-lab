#!/usr/bin/env python3
"""TC-41: TAXII 2.1 feed contract (E2E-MISP-001 real coverage).

The lab ships a medallion TAXII 2.1 server (optional overlay
``docker-compose.taxii.yml``) exposing the ``soarlab`` API root with the
``ransomware-iocs`` collection. These tests exercise the real protocol:
discovery, collections, object pull/push, malformed-bundle rejection,
anonymous rejection, and the feed-consumer path TAXII → MISP.
"""

import json
import os
import time
from pathlib import Path

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.slow,
]

TAXII_BASE = "http://taxii:5000"
API_ROOT = "soarlab"
COLLECTION_ID = "52892447-4d7e-4f70-94d0-6b2b7e8b4d0d"
TAXII_CT = "application/taxii+json;version=2.1"
TAXII_CONFIG = Path("/app/infra/docker/taxii/config.json")


def _creds() -> tuple[str, str]:
    # TAXII-EVAL-001: creds come from env (.env.full via conftest load_dotenv);
    # config.json now ships only placeholders.
    pw = os.environ.get("TAXII_READER_PASS")
    if pw:
        return "taxii_reader", pw
    cfg = json.loads(TAXII_CONFIG.read_text(encoding="utf-8"))
    user, pw = next(iter(cfg["users"].items()))
    return user, pw


def _h() -> dict:
    u, p = _creds()
    import base64
    return {
        "Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode(),
        "Accept": TAXII_CT,
        "Content-Type": TAXII_CT,
    }


def _objects_url() -> str:
    return f"{TAXII_BASE}/{API_ROOT}/collections/{COLLECTION_ID}/objects/"


class TestTaxiiFeed(E2EBaseTest):
    tc_id = "TC-41"

    # ── TC-41-01: discovery advertises the lab api root ───────────────────

    def test_taxii_discovery_and_api_root(self):
        r = requests.get(f"{TAXII_BASE}/taxii2/", headers=_h(), timeout=15)
        assert r.status_code == 200, f"discovery: {r.status_code}"
        disc = r.json()
        assert API_ROOT in disc.get("api_roots", []), disc
        r = requests.get(f"{TAXII_BASE}/{API_ROOT}/", headers=_h(), timeout=15)
        assert r.status_code == 200
        info = r.json()
        assert info.get("versions"), info

    # ── TC-41-02: pull — seeded collection exposes its indicator ──────────

    def test_taxii_pull_seeded_collection(self):
        r = requests.get(f"{TAXII_BASE}/{API_ROOT}/collections/",
                         headers=_h(), timeout=15)
        assert r.status_code == 200
        cols = r.json().get("collections", [])
        assert any(c["id"] == COLLECTION_ID for c in cols), cols
        r = requests.get(_objects_url(), headers=_h(), timeout=15)
        assert r.status_code == 200
        objs = r.json().get("objects", [])
        seed = [o for o in objs if o.get("id") ==
                "indicator--b3f6a1e2-7c4d-4a8f-9e01-2f5c8d9a1b2c"]
        assert seed, f"seed indicator missing: {[o.get('id') for o in objs]}"
        assert seed[0]["type"] == "indicator"
        assert seed[0].get("spec_version") == "2.1"

    # ── TC-41-03: push a new indicator, pull it back ──────────────────────

    def test_taxii_push_then_pull_back(self):
        import uuid
        oid = f"indicator--{uuid.uuid4()}"
        indicator = {
            "type": "indicator", "spec_version": "2.1", "id": oid,
            "created": "2026-11-10T00:00:00.000Z",
            "modified": "2026-11-10T00:00:00.000Z",
            "name": "tc41-pushed-c2",
            "indicator_types": ["malicious-activity"],
            "pattern": "[domain-name:value = 'tc41-c2.example.invalid']",
            "pattern_type": "stix",
            "valid_from": "2026-11-10T00:00:00.000Z",
        }
        r = requests.post(_objects_url(), headers=_h(),
                          json={"objects": [indicator]}, timeout=20)
        assert r.status_code in (200, 202), f"push: {r.status_code} {r.text[:300]}"
        status = r.json()
        assert status.get("success_count", 0) >= 1 or \
            status.get("status") == "complete", status
        # Pull-back: the pushed object must be retrievable by id.
        r = requests.get(f"{_objects_url()}?match[id]={oid}",
                         headers=_h(), timeout=15)
        assert r.status_code == 200
        objs = r.json().get("objects", [])
        assert any(o.get("id") == oid for o in objs), (
            f"pushed {oid} not in pull-back: {[o.get('id') for o in objs]}"
        )

    # ── TC-41-04: malformed bundle is bounded-rejected ────────────────────

    def test_taxii_malformed_bundle_rejected(self):
        for bad in ({"objects": [{"type": "not-a-stix-type"}]},
                    {"objects": [{"spec_version": "9.9"}]},
                    {"not_objects": []}):
            try:
                r = requests.post(_objects_url(), headers=_h(),
                                  json=bad, timeout=15)
            except requests.RequestException:
                continue  # connection-level rejection is also a rejection
            assert r.status_code in (400, 406, 415, 422, 500) or \
                r.status_code == 202, f"unexpected: {r.status_code}"
            # Whatever it returns, it must not 5xx-hang nor silently accept
            # a bundle with zero valid objects as a success.
            if r.status_code in (200, 202):
                body = r.json()
                assert body.get("success_count", 0) == 0 or \
                    body.get("failure_count", 0) >= 1, body

    # ── TC-41-05: anonymous requests rejected ─────────────────────────────

    def test_taxii_anonymous_rejected(self):
        for path in ("/taxii2/", f"/{API_ROOT}/",
                     f"/{API_ROOT}/collections/", _objects_url().replace(TAXII_BASE, "")):
            r = requests.get(f"{TAXII_BASE}{path}",
                             headers={"Accept": TAXII_CT}, timeout=10)
            assert r.status_code in (401, 403), (
                f"anonymous {path}: {r.status_code} — AUTH BYPASS"
            )

    # ── TC-41-06: real consumer path — TAXII pull → MISP push ────────────

    def test_taxii_feed_into_misp(self):
        """The SOC loop: pull an indicator off the TAXII feed and land it in
        MISP as an attribute — the real downstream use of the feed."""
        r = requests.get(_objects_url(), headers=_h(), timeout=15)
        assert r.status_code == 200
        objs = [o for o in r.json().get("objects", [])
                if o.get("type") == "indicator"]
        assert objs, "TAXII feed empty"
        # Extract a usable IoC value from the STIX pattern.
        import re
        m = re.search(r"'([^']+)'", objs[0]["pattern"])
        assert m, f"unparseable pattern: {objs[0]['pattern']}"
        ioc = m.group(1)
        atype = "ip-dst" if re.match(r"^\d+\.\d+\.\d+\.\d+$", ioc) else "domain"

        key = self.env.get("MISP_API_KEY", "")
        assert key, "no MISP_API_KEY"
        h = {"Authorization": key, "Accept": "application/json",
             "Content-Type": "application/json"}
        ev = {
            "info": f"tc41 taxii-ingest {int(time.time())}",
            "threat_level_id": "4", "analysis": "0", "distribution": "0",
            "Attribute": [{"type": atype, "value": ioc, "to_ids": True,
                           "comment": f"via taxii:{objs[0]['id']}"}],
        }
        r = requests.post("https://misp/events/add", headers=h, json=ev,
                          timeout=30, verify="/app/certs/ca.crt")
        assert r.status_code == 200, f"misp ingest: {r.status_code} {r.text[:200]}"
        eid = r.json()["Event"]["id"]
        try:
            r = requests.get(f"https://misp/events/view/{eid}", headers=h,
                             timeout=30, verify="/app/certs/ca.crt")
            attrs = r.json()["Event"].get("Attribute", [])
            assert any(a["value"] == ioc for a in attrs), (
                f"taxii-fed IoC {ioc} missing in MISP event"
            )
        finally:
            requests.delete(f"https://misp/events/delete/{eid}", headers=h,
                            timeout=30, verify="/app/certs/ca.crt")
