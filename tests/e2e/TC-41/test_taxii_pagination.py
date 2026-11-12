#!/usr/bin/env python3
"""TC-41 ext: TAXII 2.1 pagination (limit/next envelopes) and incremental
sync via added_after — exercised against the real medallion server."""

import json
import os
import time
from pathlib import Path

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

TAXII = "http://taxii:5000"
ROOT = f"{TAXII}/soarlab"
COLLECTION = "52892447-4d7e-4f70-94d0-6b2b7e8b4d0d"
STIX_CT = "application/taxii+json;version=2.1"
CONFIG = Path("/app/infra/docker/taxii/config.json")


def _creds() -> tuple[str, str]:
    # TAXII-EVAL-001: env-first (config.json is now a placeholder template).
    pw = os.environ.get("TAXII_READER_PASS")
    if pw:
        return "taxii_reader", pw
    cfg = json.loads(CONFIG.read_text())
    users = cfg.get("users", {})
    name = next(iter(users))
    return name, users[name]


class TestTAXIIPagination(E2EBaseTest):
    tc_id = "TC-41"

    @classmethod
    def setup_class(cls):
        cls.auth = _creds()
        cls.h_json = {"Accept": STIX_CT}
        cls.h_post = {"Accept": STIX_CT,
                      "Content-Type": STIX_CT}
        cls.url = f"{ROOT}/collections/{COLLECTION}/objects/"

    def _push(self, indicator_id: str, pattern: str) -> requests.Response:
        indicator = {
            "type": "indicator",
            "spec_version": "2.1",
            "id": f"indicator--{indicator_id}",
            "created": "2026-01-01T00:00:00Z",
            "modified": "2026-01-01T00:00:00Z",
            "pattern": pattern,
            "pattern_type": "stix",
            "valid_from": "2026-01-01T00:00:00Z",
        }
        return requests.post(self.url, json={"objects": [indicator]},
                             headers=self.h_post, auth=self.auth, timeout=15)

    def _get(self, **params) -> requests.Response:
        return requests.get(self.url, params=params, headers=self.h_json,
                            auth=self.auth, timeout=20)

    def test_pagination_limit_and_next(self):
        """Pull with a small limit: the server must return a bounded page
        (and a next token when more objects remain)."""
        prefix = f"page-{int(time.time())}"
        for i in range(6):
            iid = f"{prefix}-{i:04d}-0000-0000000000{i:02d}"
            r = self._push(iid, f"[ipv4-addr:value = '10.99.{i}.1']")
            assert r.status_code in (200, 202), r.text[:200]
        r = self._get(limit=3)
        assert r.status_code == 200, r.text[:200]
        env = r.json()
        objs = env.get("objects", [])
        assert 0 < len(objs) <= 3, f"limit not honored: {len(objs)} objects"
        if env.get("more"):
            assert env.get("next"), "more=true without next token"
            r2 = self._get(limit=3, **{"next": env["next"]})
            assert r2.status_code == 200
            assert r2.json().get("objects"), "next page empty"

    def test_added_after_incremental_sync(self):
        """added_after must return only objects added after the timestamp —
        the incremental-feed contract a TAXII consumer relies on."""
        r = self._get(**{"added_after": "2999-01-01T00:00:00Z"})
        assert r.status_code == 200
        assert not r.json().get("objects"), (
            "future added_after returned objects — filter broken"
        )
        r = self._get(**{"added_after": "2000-01-01T00:00:00Z"})
        assert r.status_code == 200
        assert r.json().get("objects"), (
            "past added_after returned nothing — filter inverted or ignored"
        )

    def test_pagination_respects_match_id_filter(self):
        """Pagination params must compose with match filters — a page
        filtered by id returns only that object."""
        iid = f"match-{int(time.time())}-0000-000000000000"
        r = self._push(iid, "[domain-name:value = 'tc41-match.lab']")
        assert r.status_code in (200, 202)
        r = self._get(limit=1, **{"match[id]": f"indicator--{iid}"})
        assert r.status_code == 200
        objs = r.json().get("objects", [])
        assert len(objs) == 1 and objs[0]["id"] == f"indicator--{iid}"
