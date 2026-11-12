"""TC-30 — DNS failure-plane boundaries.

The air-gap tests cover container disconnect; these cover the resolver
plane itself: NXDOMAIN fails fast with a typed error, a dead resolver
times out bounded, and Docker's embedded DNS keeps internal resolution
working while the egress guard kills external reachability.
"""

from __future__ import annotations

import socket
import struct
import time

import pytest
import requests


def _resolve(name: str, timeout: float = 5.0) -> tuple[float, list[str] | None, Exception | None]:
    socket.setdefaulttimeout(timeout)
    t0 = time.time()
    try:
        infos = socket.getaddrinfo(name, None)
        return time.time() - t0, [i[4][0] for i in infos], None
    except Exception as e:  # noqa: BLE001 — we classify the real error
        return time.time() - t0, None, e


def _dns_query_raw(resolver_ip: str, name: str, timeout: float = 5.0) -> tuple[float, int | None]:
    """Raw UDP DNS query — returns (elapsed, rcode). rcode None = no reply."""
    tid = 0x1234
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    packet = header + qname + struct.pack(">HH", 1, 1)
    t0 = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        try:
            s.sendto(packet, (resolver_ip, 53))
            data, _ = s.recvfrom(512)
            _, flags, _, _, _, _ = struct.unpack(">HHHHHH", data[:12])
            return time.time() - t0, flags & 0xF
        except socket.timeout:
            return time.time() - t0, None


@pytest.mark.e2e
class TestDnsBoundaries:
    tc_id = "TC-30"

    def test_nxdomain_fails_fast_typed(self):
        """An unresolvable name returns gaierror in <5s — typed failure,
        never a silent hang."""
        elapsed, addrs, err = _resolve("no-such-host-tc30.invalid", timeout=5.0)
        assert addrs is None and err is not None
        assert isinstance(err, socket.gaierror)
        assert elapsed < 5.0, f"NXDOMAIN took {elapsed:.1f}s — not fast-fail"

    def test_dns_cannot_bypass_embedded_resolver(self):
        """A raw DNS query to an external resolver IP is intercepted by
        Docker's embedded resolver and REFUSED in bounded time — the DNS
        egress path cannot be bypassed (rcode 5 = REFUSED)."""
        elapsed, rcode = _dns_query_raw("10.255.255.1", "example.com", timeout=4.0)
        assert elapsed < 4.0, f"intercepted query hung: {elapsed:.1f}s"
        assert rcode == 5, (
            f"expected REFUSED (5) from embedded resolver, got rcode={rcode}"
        )

    def test_internal_resolves_external_unreachable(self):
        """Internal docker names resolve and are reachable; external names
        do NOT resolve at all — the guard boundary extends to the DNS plane."""
        _, internal, err_i = _resolve("thehive")
        assert err_i is None and internal, f"internal DNS broken: {err_i}"

        _, public, err_p = _resolve("example.com")
        assert err_p is not None or not public, (
            f"external name resolved to {public} — DNS egress open?"
        )

        r = requests.get("https://thehive:9443/api/v1/status/public", timeout=10)
        assert r.status_code == 200

    def test_dns_failures_leave_api_healthy(self):
        """After NXDOMAIN + refused-resolver probes the API keeps serving —
        resolver failures don't wedge the process."""
        _resolve("probe1.invalid", timeout=3)
        _dns_query_raw("10.255.255.2", "x.example", timeout=2.0)
        r = requests.get("http://localhost:8000/health", timeout=10)
        assert r.status_code == 200
