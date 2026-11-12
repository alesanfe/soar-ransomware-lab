"""TC-20 — full service×port matrix, docker-socket exposure, IPv6, egress.

Guards the hardening invariants that regressed silently once before (the api
was recreated without the hardened overlay and regained a raw RW docker
socket): no raw socket mount, proxy verb whitelist enforced, no service
listening on 2375, no IPv6, egress blocked.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest
import requests

PROXY = "http://docker-socket-proxy:2375"

SERVICES = {
    "thehive": 9000,
    "cortex": 9001,
    "elasticsearch": 9200,
    "misp": 443,
    "redis": 6379,
    "loki": 3100,
    "taxii": 5000,
    "grafana": 3000,
}
# foreign ports each host must NOT listen on
FOREIGN_PORTS = {9000, 9001, 9200, 443, 6379, 3100, 5000, 3000}


def _probe(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.mark.e2e
class TestNetworkMatrix:
    def test_api_has_no_raw_docker_socket(self):
        """CIS 5.31 — the api must reach the daemon only via the proxy."""
        assert not os.path.exists("/var/run/docker.sock"), (
            "raw docker.sock mounted into api — hardened overlay lost"
        )
        host = os.environ.get("DOCKER_HOST", "")
        assert "docker-socket-proxy" in host, (
            f"DOCKER_HOST={host!r} — api must not hold the daemon socket"
        )

    def test_docker_proxy_denies_privileged_verbs(self):
        """The socket-proxy whitelist must block cluster/secrets verbs."""
        allowed = requests.get(f"{PROXY}/info", timeout=10)
        assert allowed.status_code == 200, "proxy not reachable"
        for verb in ("/secrets", "/nodes", "/swarm", "/services"):
            r = requests.get(f"{PROXY}{verb}", timeout=10)
            assert r.status_code == 403, (
                f"docker-proxy allowed {verb}: {r.status_code} — whitelist broken"
            )

    def test_no_service_exposes_docker_tcp(self):
        """Nothing except the proxy may listen on the docker API port."""
        for host in SERVICES:
            assert not _probe(host, 2375), f"{host}:2375 open — unprotected docker API"

    def test_full_service_port_matrix(self):
        """Each service listens on its own port; sampled foreign ports closed."""
        for host, own in SERVICES.items():
            assert _probe(host, own), f"{host}:{own} unreachable (service down?)"
            for port in sorted(FOREIGN_PORTS - {own})[:3]:
                assert not _probe(host, port), (
                    f"{host}:{port} open — cross-service port bleed"
                )

    def test_egress_external_ip_blocked(self):
        """Outbound to arbitrary internet IP:port must be refused or timeout."""
        for ip, port in (("8.8.8.8", 53), ("1.1.1.1", 443)):
            assert not _probe(ip, port, timeout=3.0), (
                f"egress {ip}:{port} OPEN — unrestricted outbound from api"
            )

    def test_no_ipv6_global_address(self):
        """No non-loopback IPv6 — prevents policy bypass on an unaudited path.

        /proc/net/if_inet6 rows are `addr idx plen scope flags iface`; scope
        0x00 is global. Loopback (::1 scope 0x10) is expected.
        """
        try:
            rows = Path("/proc/net/if_inet6").read_text().splitlines()
        except FileNotFoundError:
            return  # no IPv6 stack at all — the strongest form of the contract
        offenders = [r for r in rows if r.split()[-1] != "lo" or r.split()[3] == "00"]
        assert not offenders, f"non-loopback/global IPv6 present: {offenders}"
