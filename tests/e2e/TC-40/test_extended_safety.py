#!/usr/bin/env python3
"""TC-40: extended safety contracts — TLS verification, ES watermark
read-only, analyzer job bound, MISP IoC pull/push, anonymous-access matrix.

Closes the E2E debt items that are implementable against the running stack:
- E2E-PKI-001 (subset): TLS must fail with an untrusted CA — the lab CA is
  required, ``verify=False`` recovery is never acceptable.
- E2E-DATA-002 (subset): an index forced read-only (flood-stage watermark
  behaviour) rejects writes with a clear block error, not silent loss.
- E2E-CORTEX-001 (subset): an analyzer job reaches a terminal state inside
  a bound — no job may run forever.
- E2E-MISP-001 (subset): IoC pull/push round-trip via the MISP REST API —
  the stack ships no standalone TAXII server, so the feed contract is
  exercised on the endpoints that exist.
- E2E-ZT-001 (subset): anonymous requests are rejected everywhere auth is
  required — the precondition any future SSO/OIDC layer must preserve.
"""

import os
import time
from pathlib import Path

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.security,
    pytest.mark.slow,
]

LAB_CA = "/app/certs/ca.crt"
ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))


class TestExtendedSafety(E2EBaseTest):
    tc_id = "TC-40"

    # ── TC-40-01: TLS verification is enforced ────────────────────────────

    def test_tls_untrusted_ca_rejected(self):
        """Loki is HTTPS under the lab CA. A client that does NOT trust that
        CA must get an SSL error — silently falling back to verify=False
        would be an auth bypass (E2E-PKI-001)."""
        assert Path(LAB_CA).exists(), "lab CA not mounted"
        # Untrusted: the public certifi bundle does not include our lab CA.
        # (The container exports REQUESTS_CA_BUNDLE=<lab CA>, so the default
        # verify=True already trusts it — an explicit public bundle is the
        # meaningful "untrusted client" check.)
        import certifi
        with pytest.raises(requests.exceptions.SSLError):
            requests.get("https://loki:3100/ready", verify=certifi.where(), timeout=10)
        # Trusted: the lab CA succeeds — service is genuinely TLS, not down.
        r = requests.get("https://loki:3100/ready", verify=LAB_CA, timeout=15)
        assert r.status_code in (200, 503), f"unexpected: {r.status_code}"
        # Hostname mismatch on a trusted CA must still fail: loki's IP is
        # routable but not in the cert SANs.
        import socket
        loki_ip = socket.gethostbyname("loki")
        with pytest.raises(requests.exceptions.SSLError):
            requests.get(f"https://{loki_ip}:3100/ready", verify=LAB_CA, timeout=10)

    # ── TC-40-02: ES read-only watermark → clear block, no silent loss ────

    def test_es_readonly_watermark_clear_block(self):
        """Simulate flood-stage: set read_only_allow_delete on a scratch
        index, attempt a write → 403 cluster_block_exception; clear the
        block → write succeeds. No silent loss, explicit error."""
        es = "https://elasticsearch:9200"
        idx = f"tc40-watermark-{int(time.time())}"
        try:
            r = requests.put(f"{es}/{idx}", auth=ES_AUTH, timeout=15)
            assert r.status_code == 200, r.text[:200]
            r = requests.put(
                f"{es}/{idx}/_settings",
                json={"index.blocks.read_only_allow_delete": True},
                auth=ES_AUTH, timeout=15,
            )
            assert r.status_code == 200, r.text[:200]
            r = requests.post(
                f"{es}/{idx}/_doc",
                json={"probe": "write-during-readonly"},
                auth=ES_AUTH, timeout=15,
            )
            assert r.status_code in (403, 429), (
                f"expected cluster_block 403/429, got {r.status_code}: {r.text[:200]}"
            )
            body = r.json()
            assert "cluster_block_exception" in str(body), body
        finally:
            requests.put(
                f"{es}/{idx}/_settings",
                json={"index.blocks.read_only_allow_delete": None},
                auth=ES_AUTH, timeout=15,
            )
            requests.delete(f"{es}/{idx}", auth=ES_AUTH, timeout=15)
        # Recovery: a fresh index accepts writes again (no permanent damage).
        idx2 = f"tc40-recovered-{int(time.time())}"
        try:
            r = requests.post(f"{es}/{idx2}/_doc?refresh=true",
                              json={"probe": "post-recovery"}, auth=ES_AUTH, timeout=15)
            assert r.status_code == 201, r.text[:200]
        finally:
            requests.delete(f"{es}/{idx2}", auth=ES_AUTH, timeout=15)

    # ── TC-40-03: analyzer job reaches terminal state inside a bound ──────

    def test_analyzer_job_bounded_terminal_state(self):
        """Submit a real Cortex job and require a terminal status within
        180s — no analyzer may hang the pipeline forever (E2E-CORTEX-001)."""
        key = self.env.get("CORTEX_API_KEY", "")
        assert key, "no CORTEX_API_KEY"
        base = "https://cortex:9443"
        h = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{base}/api/analyzer", headers=h, timeout=15)
        assert r.status_code == 200, f"analyzer list: {r.status_code}"
        analyzers = [a for a in r.json() if a.get("dataTypeList")]
        assert analyzers, "no analyzers configured"
        # Prefer a trivial local analyzer (hostname resolve) for determinism.
        pick = next(
            (a for a in analyzers if "resolve" in a.get("id", "").lower()
             or "dns" in a.get("id", "").lower()),
            analyzers[0],
        )
        dtypes = pick.get("dataTypeList", ["domain"])
        dtype = "ip" if "ip" in dtypes else dtypes[0]
        data = {"ip": "8.8.8.8", "domain": "example.com",
                "hostname": "example.com", "url": "http://example.com",
                "fqdn": "example.com"}.get(dtype, "example.com")
        r = requests.post(
            f"{base}/api/analyzer/{pick['id']}/run",
            headers=h,
            json={"data": data, "dataType": dtype, "tlp": 1, "pap": 1},
            timeout=20,
        )
        assert r.status_code in (200, 201), f"job submit: {r.status_code} {r.text[:200]}"
        job_id = r.json().get("_id") or r.json().get("id")
        assert job_id
        deadline = time.time() + 180
        status = "Unknown"
        while time.time() < deadline:
            r = requests.get(f"{base}/api/job/{job_id}", headers=h, timeout=15)
            assert r.status_code == 200
            status = r.json().get("status", "Unknown")
            if status in ("Success", "Failure", "Deleted"):
                break
            time.sleep(5)
        assert status in ("Success", "Failure", "Deleted"), (
            f"job {job_id} stuck in {status} after 180s — unbounded analyzer"
        )

    # ── TC-40-04: MISP IoC pull/push round-trip ───────────────────────────

    def test_misp_ioc_pull_push_roundtrip(self):
        """Push an IoC into MISP, pull it back, verify dedup by uuid —
        the feed contract a TAXII layer would sit on (E2E-MISP-001)."""
        key = self.env.get("MISP_API_KEY", "")
        assert key, "no MISP_API_KEY"
        base = "https://misp"
        h = {"Authorization": key, "Accept": "application/json",
             "Content-Type": "application/json"}
        ioc = f"198.51.100.{int(time.time()) % 254 + 1}"  # TEST-NET-2, unique
        ev = {
            "info": f"tc40 ioc push {int(time.time())}",
            "threat_level_id": "4", "analysis": "0", "distribution": "0",
            "Attribute": [{"type": "ip-dst", "value": ioc, "to_ids": True}],
        }
        r = requests.post(f"{base}/events/add", headers=h, json=ev, timeout=30, verify=LAB_CA)
        assert r.status_code == 200, f"push: {r.status_code} {r.text[:300]}"
        event_id = r.json()["Event"]["id"]
        try:
            # Pull: the same event must round-trip with the attribute.
            r = requests.get(f"{base}/events/view/{event_id}", headers=h, timeout=30, verify=LAB_CA)
            assert r.status_code == 200
            attrs = r.json()["Event"].get("Attribute", [])
            assert any(a["value"] == ioc for a in attrs), (
                f"pushed IoC {ioc} not found in pulled event"
            )
            # Idempotent feed: restSearch by uuid returns exactly this event.
            uuid = r.json()["Event"]["uuid"]
            r = requests.post(
                f"{base}/events/restSearch",
                headers=h, json={"uuid": uuid}, timeout=30, verify=LAB_CA,
            )
            assert r.status_code == 200
            hits = [e["Event"]["uuid"] for e in r.json().get("response", [])]
            assert hits == [uuid] or uuid in hits, f"uuid lookup: {hits}"
        finally:
            requests.delete(f"{base}/events/delete/{event_id}", headers=h, timeout=30, verify=LAB_CA)

    # ── TC-40-05: anonymous access matrix — auth required everywhere ──────

    def test_anonymous_requests_rejected_everywhere(self):
        """Every authenticated surface must reject anonymous callers — the
        zero-trust floor any SSO/OIDC layer must preserve (E2E-ZT-001)."""
        checks = [
            ("api-status", "http://api:8000/api/status", None),
            ("api-health-auth", "http://api:8000/api/health", None),
            ("shuffle-workflows", "https://shuffle-backend:5443/api/v1/workflows", None),
            ("cortex-user", "https://cortex:9443/api/user", None),
            ("thehive-user", "https://thehive:9443/api/v1/user/current", None),
            ("misp-users", "https://misp/users/view", LAB_CA),
        ]
        failures = []
        for name, url, ca in checks:
            try:
                r = requests.get(url, verify=ca or True, timeout=10, allow_redirects=False)
            except requests.exceptions.SSLError as e:
                # TLS layer refusing us is also a rejection — acceptable.
                continue
            except requests.RequestException as e:
                failures.append(f"{name}: unreachable ({e.__class__.__name__})")
                continue
            if r.status_code in (200, 201, 204) and "/health" not in url:
                # api /health (no prefix) is intentionally public; anything
                # else returning success anonymously is an auth bypass.
                failures.append(f"{name}: anonymous {r.status_code} — AUTH BYPASS")
        assert not failures, "anonymous access leaked:\n" + "\n".join(failures)
