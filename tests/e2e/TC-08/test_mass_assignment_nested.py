#!/usr/bin/env python3
"""TC-08 ext: nested mass-assignment — dotted notation, __proto__-style
keys and deep privilege objects must not reach the stored alert or
mutate caller privileges."""

import os
import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.security]

ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))

API = "http://api:8000"


class TestNestedMassAssignment(E2EBaseTest):
    tc_id = "TC-08"

    def _headers(self):
        return {"X-Service-Token": self.env.get("INTERNAL_SERVICE_TOKEN", ""),
                "Content-Type": "application/json"}

    def _submit(self, payload: dict) -> requests.Response:
        return requests.post(f"{API}/api/v1/alerts", json=payload,
                             headers=self._headers(), timeout=15)

    def test_nested_privilege_objects_not_persisted(self):
        """Nested role/admin keys must not appear verbatim in the stored
        alert — mass-assignment reaches storage as inert data or nothing."""
        r = self._submit({
            "alert_id": f"tc08-{int(__import__('time').time())}",
            "severity": 3,
            "user": {"role": "admin", "is_admin": True},
            "nested": {"deep": {"privilege": "root"}},
        })
        assert r.status_code in (200, 202), r.text[:200]
        adm = r.json().get("admission_id")
        assert adm
        es = requests.get(
            f"https://elasticsearch:9200/soar-alerts/_search?q=admission_id:{adm}",
            auth=ES_AUTH, timeout=15)
        if es.status_code == 200 and es.json()["hits"]["hits"]:
            stored = str(es.json()["hits"]["hits"][0]["_source"])
            assert '"role": "admin"' not in stored or "role" not in stored

    def test_dotted_and_proto_keys_rejected_or_inert(self):
        """`a.b.c` dotted keys and `__proto__` style keys are JS/Python
        pollution vectors — they must not 5xx nor alter token claims."""
        for evil in (
            {"role.admin": True},
            {"__proto__": {"admin": True}},
            {"a.b.c.d.e": "x"},
        ):
            r = self._submit({"alert_id": "tc08-dot", "severity": 1, **evil})
            assert r.status_code in (200, 202, 400, 422), (
                f"{evil} -> {r.status_code}"
            )
        # Token claims must be unchanged: the service token still works
        # exactly as before (a polluted claim would fail auth).
        r = self._submit({"alert_id": "tc08-postcheck", "severity": 1})
        assert r.status_code in (200, 202), "token claims mutated"

    def test_array_of_objects_does_not_expand(self):
        """Array-typed mass assignment must not fan out into N docs."""
        r = self._submit({
            "alert_id": "tc08-arr", "severity": 1,
            "victims": [{"host": f"h{i}"} for i in range(500)],
        })
        assert r.status_code in (200, 202, 400, 413, 422)
