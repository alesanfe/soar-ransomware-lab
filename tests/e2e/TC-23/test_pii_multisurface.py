"""TC-23 — multi-artifact PII dictionary scan.

TC-23's base test verifies masking in ES/TheHive/Loki. This adds the missing
surface: generated artifacts (JUnit XML reports embed stdout/stderr echoes of
every payload) scanned with a PII *dictionary* — emails, SSNs, card numbers,
phone formats, common secret shapes. Synthetic canary values owned by the
test run are exempt; anything else matching the dictionary fails the gate.
"""

from __future__ import annotations

import re
from pathlib import Path

import os
import pytest
import requests

from tests.e2e.base import E2EBaseTest

ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))

JUNIT_DIR = Path("/app/reports/junit")

PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "phone_intl": re.compile(r"\+\d{10,15}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
}
# allow-list: values the test-suite legitimately embeds (synthetic + infra)
ALLOWLIST = re.compile(
    r"(example\.(com|org)|soar\.local|@test\.|localhost|thehive\.local|"
    r"misp\.local|cortex\.local|noreply@|user@example|analyst@soar|"
    r"admin@thehive|test@test|example@|@soar\.)",
    re.IGNORECASE,
)


def _scan_text(text: str, source: str) -> list[str]:
    hits = []
    for name, rx in PII_PATTERNS.items():
        for m in rx.finditer(text):
            val = m.group(0)
            if ALLOWLIST.search(val):
                continue
            hits.append(f"{source}:{name}:{val[:40]}")
    return hits


@pytest.mark.e2e
class TestPiiMultiSurface(E2EBaseTest):
    tc_id = "TC-23"

    def test_junit_artifacts_carry_no_real_pii(self):
        """Every JUnit XML is scanned — captured stdout echoes full payloads."""
        if not JUNIT_DIR.exists():
            pytest.skip("no junit artifacts yet")
        findings = []
        for xml in sorted(JUNIT_DIR.glob("*.xml")):
            findings += _scan_text(xml.read_text(errors="replace"), xml.name)
        assert not findings, (
            f"PII dictionary matched in artifacts:\n" + "\n".join(findings[:20])
        )

    def test_stored_metrics_doc_carries_no_unmasked_pii(self):
        """PII canary submitted -> stored doc must mask or drop it."""
        canary_email = f"pii-{self.uid('c')}@canary.invalid"
        canary_ssn = "999-12-3456"
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        payload["user_email"] = canary_email
        payload["user_ssn"] = canary_ssn
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        import time

        time.sleep(3)
        r = requests.post(
            "https://elasticsearch:9200/soar-metrics/_search",
            json={"size": 5, "query": {"term": {"alert_id": payload["alert_id"]}}},
            auth=ES_AUTH, timeout=15,
        )
        hits = r.json().get("hits", {}).get("hits", [])
        for h in hits:
            src = str(h["_source"])
            assert canary_email not in src, "raw email landed in soar-metrics"
            assert canary_ssn not in src, "raw SSN landed in soar-metrics"

    def test_loki_streams_carry_no_raw_canary(self):
        """Same canary must not appear verbatim in Loki streams."""
        canary = f"PIICANARY{self.uid('x').replace('-', '')}"
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        payload["user_note"] = canary
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        import time
        from pathlib import Path as _P

        time.sleep(4)
        ca = _P("/app/certs/ca.crt")
        try:
            r = requests.get(
                "https://loki:3100/loki/api/v1/query_range",
                params={
                    "query": f'{{job=~".+"}} |= "{canary}"',
                    "start": int((time.time() - 900) * 1e9),
                    "end": int(time.time() * 1e9),
                    "limit": 10,
                },
                verify=str(ca) if ca.exists() else False,
                timeout=15,
            )
            data = r.json()
            results = data.get("data", {}).get("result", [])
            leaked = sum(len(s.get("values", [])) for s in results)
            assert leaked == 0, f"canary leaked to Loki x{leaked}"
        except requests.RequestException:
            pytest.skip("loki unreachable — surface not testable this run")
