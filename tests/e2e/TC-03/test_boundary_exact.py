#!/usr/bin/env python3
"""TC-03/TC-29 ext: exact ±1B boundary on the real ingest edge
(nginx /shuffle-api/ client_max_body_size 2m) and JSON depth DoS."""

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.security]

EDGE = "https://nginx/shuffle-api/webhook"
LIMIT = 2 * 1024 * 1024  # client_max_body_size 2m


class TestExactBoundary(E2EBaseTest):
    tc_id = "TC-03"

    def _post_bytes(self, n: int) -> requests.Response:
        return requests.post(
            EDGE, data=b"x" * n,
            headers={"Content-Type": "application/json"},
            verify=self.s.verify, timeout=30,
        )

    def test_limit_minus_1b_passes_edge(self):
        """2MiB-1 must cross the edge — any non-413 status means the body
        reached the backend (400/404 from backend ≠ edge rejection)."""
        r = self._post_bytes(LIMIT - 1)
        assert r.status_code != 413, "edge rejected a sub-limit body"

    def test_limit_plus_1b_rejected(self):
        """2MiB+1 must be rejected AT the edge with 413 — the DoS bound."""
        r = self._post_bytes(LIMIT + 1)
        assert r.status_code == 413, f"edge accepted oversized body: {r.status_code}"

    def test_json_depth_bounded(self):
        """Deeply nested JSON must not hang the pipeline — bounded 4xx or
        a clean accept, never an unbounded parse."""
        depth = 500
        payload = b'{"a":' * depth + b"1" + b"}" * depth
        r = requests.post(
            "http://api:8000/api/v1/alerts", data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Service-Token": self.env.get("INTERNAL_SERVICE_TOKEN", ""),
            },
            timeout=30,
        )
        assert r.status_code in (200, 202, 400, 413, 422), (
            f"deep nesting produced {r.status_code}"
        )
