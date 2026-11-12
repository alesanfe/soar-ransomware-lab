#!/usr/bin/env python3
"""TC-07 ext: structured error contract — every API error must be
machine-readable (code+field+message) and carry the correlation id."""

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.functional]

API = "http://localhost:8000"


class TestStructuredErrorContract(E2EBaseTest):
    tc_id = "TC-07"

    def test_422_field_pinpointed_contract(self):
        """Validation errors expose the exact failing field — the
        {code,type + field,loc + message} triple clients need to localize
        errors without parsing prose."""
        r = requests.post(f"{API}/auth/login", json={}, timeout=10)
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert isinstance(detail, list) and detail, "not a structured error"
        fields = {tuple(e.get("loc", []))[-1] for e in detail}
        assert "username" in fields and "password" in fields, fields
        for e in detail:
            assert e.get("type") and e.get("msg"), e
            assert e["loc"][0] == "body", e

    def test_401_machine_readable_with_correlation(self):
        r = requests.post(f"{API}/api/v1/alerts", json={"a": 1}, timeout=10)
        assert r.status_code == 401
        assert isinstance(r.json().get("detail"), str)
        assert r.headers.get("x-request-id"), "no correlation id on error"

    def test_404_machine_readable_with_correlation(self):
        r = requests.get(f"{API}/api/v1/definitely-not-a-route", timeout=10,
                         headers={"X-Service-Token":
                                  self.env.get("INTERNAL_SERVICE_TOKEN", "")})
        assert r.status_code in (404,)
        assert "detail" in r.json()
        assert r.headers.get("x-request-id")

    def test_error_responses_are_json(self):
        """Every application-level error is JSON — a client never has to
        parse HTML/plaintext to handle an API failure."""
        for url, method in [
            (f"{API}/auth/login", "post"),
            (f"{API}/api/v1/alerts", "post"),
        ]:
            r = getattr(requests, method)(url, json={}, timeout=10)
            assert "application/json" in r.headers.get("content-type", ""), (
                f"{url} returned non-JSON error: {r.headers.get('content-type')}"
            )
