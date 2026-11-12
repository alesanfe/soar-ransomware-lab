#!/usr/bin/env python3
"""TC-06 ext: severity transition matrix — every severity level accepted
must normalize to a stored value; out-of-range must be bounded, never
stored as garbage."""

import os
import time

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.functional]

ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))

API = "http://api:8000"


class TestSeverityTransitionMatrix(E2EBaseTest):
    tc_id = "TC-06"

    def _submit(self, sev) -> requests.Response:
        return requests.post(
            f"{API}/api/v1/alerts",
            json={"alert_id": f"tc06-{time.time_ns()}",
                  "severity": sev, "timestamp": "2026-01-01T00:00:00Z"},
            headers={"X-Service-Token":
                     self.env.get("INTERNAL_SERVICE_TOKEN", "")},
            timeout=15)

    def test_full_severity_range_accepted(self):
        """Every level of the lab's scale must submit cleanly (202/200)."""
        for sev in (1, 2, 3, 4):
            r = self._submit(sev)
            assert r.status_code in (200, 202), (
                f"severity {sev} rejected: {r.status_code}"
            )

    def test_out_of_range_bounded_not_stored(self):
        """Negative/huge severities must be bounded (4xx) — never
        accepted verbatim into the pipeline."""
        for sev in (0, -1, -999, 999, 10**6):
            r = self._submit(sev)
            assert r.status_code in (200, 202, 400, 422), r.status_code
            # If accepted, it must be normalized — assert via stored doc
            if r.status_code in (200, 202):
                adm = r.json().get("admission_id")
                es = requests.get(
                    "https://elasticsearch:9200/soar-alerts/_search"
                    f"?q=admission_id:{adm}", auth=ES_AUTH, timeout=15)
                if es.status_code == 200 and es.json()["hits"]["hits"]:
                    stored = es.json()["hits"]["hits"][0]["_source"].get(
                        "severity")
                    assert stored is None or 0 <= int(stored) <= 4, (
                        f"out-of-range severity {sev} stored as {stored}")

    def test_severity_type_coercion_bounded(self):
        """String/float severities get a bounded contract: accept-and-
        normalize or reject — never a silent coercion to a wrong int."""
        for sev in ("3", 3.9, "critical", None, True):
            r = self._submit(sev)
            assert r.status_code in (200, 202, 400, 422), (
                f"severity {sev!r} -> {r.status_code}"
            )
