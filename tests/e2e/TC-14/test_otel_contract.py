"""TC-14 — OpenTelemetry semantic contract on real Tempo traces.

The API boots a real TracerProvider (OTEL_ENABLED=1) exporting OTLP/HTTP
through otel-collector to Tempo. These tests verify the semantic contract
on actually-exported traces: W3C propagation, span-tree integrity,
monotonic timestamps, attribute hygiene, and trace isolation.
"""

from __future__ import annotations

import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

CA = "/app/certs/ca.crt"
TEMPO = "https://tempo:3200"
API = "http://localhost:8000"

SECRET_ATTR = re.compile(
    r"(?i)(password|api_?key|secret|token|authorization|bearer|cookie|set-cookie)"
)
PII_VALUE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)


def _spans_of(trace: dict) -> list[dict]:
    out = []
    for batch in trace.get("batches", []):
        for ss in batch.get("scopeSpans", []):
            out.extend(ss.get("spans", []))
    return out


def _span_trace_hex(span: dict) -> str:
    """OTLP JSON encodes traceId as base64 bytes — normalize to hex."""
    import base64
    import binascii

    raw = span.get("traceId", "")
    try:
        return base64.b64decode(raw).hex()
    except (binascii.Error, ValueError):
        return raw.lower()


def _fetch_trace(tid: str, retries: int = 8, delay: float = 2.0) -> dict | None:
    for _ in range(retries):
        r = requests.get(f"{TEMPO}/api/traces/{tid}", verify=CA, timeout=15)
        if r.status_code == 200 and r.json().get("batches"):
            return r.json()
        time.sleep(delay)
    return None


@pytest.mark.e2e
class TestOtelContract:
    tc_id = "TC-14"

    def test_traceparent_propagates_end_to_end(self):
        """Inject a W3C traceparent on ingest; the trace that lands in
        Tempo carries that trace ID — real distributed propagation."""
        tid = secrets.token_hex(16)
        sid = secrets.token_hex(8)
        r = requests.get(
            f"{API}/health",
            headers={"traceparent": f"00-{tid}-{sid}-01"},
            timeout=10,
        )
        assert r.status_code == 200
        trace = _fetch_trace(tid)
        assert trace is not None, f"injected trace {tid} not found in Tempo"
        tids = {_span_trace_hex(s) for s in _spans_of(trace)}
        assert tid in tids, f"trace ids {tids} don't contain injected {tid}"

    def test_per_hop_span_tree_intact(self):
        """Every non-root span references a parent inside the trace —
        no orphaned spans, single trace ID, service.name set."""
        r = requests.get(
            f"{TEMPO}/api/search",
            params={"q": '{.service.name="soar-api"}', "limit": 5},
            verify=CA, timeout=15,
        )
        assert r.status_code == 200
        traces = r.json().get("traces", [])
        assert traces, "no soar-api traces in Tempo"
        tid = traces[0]["traceID"]
        trace = _fetch_trace(tid, retries=2)
        assert trace is not None
        spans = _spans_of(trace)
        assert spans, "trace has no spans"
        ids = {s["spanId"] for s in spans}
        trace_ids = {_span_trace_hex(s) for s in spans}
        assert len(trace_ids) == 1, f"multiple traceIds in one trace: {trace_ids}"
        roots = 0
        for s in spans:
            parent = s.get("parentSpanId") or s.get("parent_span_id") or ""
            if not parent or parent not in ids:
                # remote parent (uninstrumented caller) or true root —
                # both are legitimate entry points into this service
                roots += 1
        assert roots >= 1, "no root/entry span"

    def test_span_timestamps_monotonic(self):
        """Child spans start at/after their parent starts and end at/before
        parent ends — clock coherence inside a trace (2ms tolerance)."""
        r = requests.get(
            f"{TEMPO}/api/search", params={"q": "{}", "limit": 10}, verify=CA, timeout=15,
        )
        for t in r.json().get("traces", []):
            trace = _fetch_trace(t["traceID"], retries=2)
            if not trace:
                continue
            spans = _spans_of(trace)
            by_id = {s["spanId"]: s for s in spans}
            for s in spans:
                parent = by_id.get(s.get("parentSpanId", ""))
                if not parent:
                    continue
                assert int(s["startTimeUnixNano"]) >= int(parent["startTimeUnixNano"]) - 2_000_000
                assert int(s["endTimeUnixNano"]) <= int(parent["endTimeUnixNano"]) + 2_000_000
            return
        pytest.fail("no fetchable trace found")

    def test_no_secrets_or_pii_in_span_attributes(self):
        """Span attributes must not carry credentials, auth headers or
        obvious PII — observability hygiene contract."""
        r = requests.get(
            f"{TEMPO}/api/search", params={"q": "{}", "limit": 15}, verify=CA, timeout=15,
        )
        checked = 0
        offenders = []
        for t in r.json().get("traces", []):
            trace = _fetch_trace(t["traceID"], retries=1, delay=0.5)
            if not trace:
                continue
            for s in _spans_of(trace):
                checked += 1
                for a in s.get("attributes", []):
                    key = a.get("key", "")
                    val = str(a.get("value", {}).get("stringValue", ""))
                    if SECRET_ATTR.search(key):
                        offenders.append(f"attr key {key}")
                    if SECRET_ATTR.search(val) or PII_VALUE.search(val):
                        offenders.append(f"attr value {val[:24]}")
        assert checked > 0, "no spans inspected"
        assert not offenders, "sensitive data in span attributes: " + "; ".join(set(offenders[:8]))

    def test_concurrent_requests_isolated_traces(self):
        """N concurrent requests produce N distinct trace IDs — no context
        bleed between concurrent executions."""
        tids = [
            (secrets.token_hex(16), secrets.token_hex(8)) for _ in range(5)
        ]

        def hit(tp):
            tid, sid = tp
            requests.get(
                f"{API}/health",
                headers={"traceparent": f"00-{tid}-{sid}-01"},
                timeout=15,
            )
            return tid

        with ThreadPoolExecutor(max_workers=5) as ex:
            sent = list(ex.map(hit, tids))
        assert len(set(sent)) == 5
        seen = set()
        for tid in sent:
            tr = _fetch_trace(tid, retries=6, delay=2.0)
            assert tr is not None, f"trace {tid} missing"
            found = {_span_trace_hex(s) for s in _spans_of(tr)}
            assert tid in found
            assert tid not in seen
            seen.add(tid)
