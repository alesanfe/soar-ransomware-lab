"""Architecture gates — CORE-STACK (ISO 27001 A.8/A.12/A.13, CIS 4/5/12,
NIST CSF PR.PS).

Permanent invariants for the core SOAR services (Elasticsearch, OpenSearch,
Redis, TheHive, Cortex, Shuffle):

- TLS interno: Redis TLS-only, ES/OpenSearch xpack http+transport TLS,
  TheHive/Cortex TLS listeners, lab PKI certs mounted.
- Segmentación: ti_net is internal (no egress); every published port binds
  to 127.0.0.1 — zero 0.0.0.0 exposure.
- Alta disponibilidad: restart policy + healthcheck + resource limits +
  log rotation on every core service.
- Hardening: no-new-privileges / cap_drop in the hardened overlay.
- Credenciales: critical secrets use :?required expansion (fail-fast), and
  SSL-verify opt-outs must default to verify-on.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "docker" / "compose"
CORE = (COMPOSE / "docker-compose.core.yml").read_text(encoding="utf-8")
MAIN = (COMPOSE / "docker-compose.yml").read_text(encoding="utf-8")
OS_COMPOSE = (COMPOSE / "docker-compose.opensearch.yml").read_text(encoding="utf-8")
HARDENED = (COMPOSE / "docker-compose.hardened.yml").read_text(encoding="utf-8")

CORE_YML = yaml.safe_load(CORE)
MAIN_YML = yaml.safe_load(MAIN)


def _published_ports(yml_text: str) -> list[str]:
    return re.findall(r'-\s*"(\d[^"]*:\d[^"]*)"', yml_text)


class TestInternalTLS:
    """ISO A.13.1 / CIS 12 — encryption in transit between services."""

    def test_redis_is_tls_only(self):
        assert "--port 0 --tls-port 6379" in CORE
        for cert in ("redis.crt", "redis.key", "ca.crt"):
            assert f"certs/{cert}:/etc/redis/tls/{cert}:ro" in CORE

    def test_redis_secret_is_mounted_not_inlined(self):
        # CORE-EVAL: --requirepass must read /run/secrets at container runtime
        # ($$ escapes compose interpolation) so the password never lands in
        # `docker inspect` entrypoint args.
        assert '--requirepass \\"$$(cat /run/secrets/redis_password)\\"' in CORE or (
            "--requirepass \"$$(cat /run/secrets/redis_password)\"" in CORE
        )
        assert "${REDIS_PASSWORD}" not in CORE.split("entrypoint", 1)[1][:400]
        yml = yaml.safe_load(CORE)
        secrets = CORE_YML.get("secrets") or {}
        assert "redis_password" in secrets
        svc = CORE_YML["services"]["redis"]
        assert "redis_password" in (svc.get("secrets") or [])
        # Hardened overlay repeats the entrypoint — same runtime-read required.
        hardened_redis = HARDENED[HARDENED.index("  redis:") :]
        assert "$$(cat /run/secrets/redis_password)" in hardened_redis

    def test_redis_healthcheck_is_a_real_tls_ping(self):
        svc = CORE_YML["services"]["redis"]
        test = " ".join(str(t) for t in svc["healthcheck"]["test"])
        assert "redis-cli" in test and "--tls" in test and "ping" in test, (
            "redis healthcheck must ping over TLS+auth, not just nc -z"
        )

    def test_elasticsearch_xpack_tls(self):
        for k in (
            "xpack.security.enabled=${ELASTIC_SECURITY_ENABLED:-true}",
            "xpack.security.http.ssl.enabled=${ELASTIC_HTTP_SSL_ENABLED:-true}",
            "xpack.security.transport.ssl.enabled=${ELASTIC_TRANSPORT_SSL_ENABLED:-true}",
        ):
            assert k in MAIN
        # Transport TLS verifies the certificate — no 'none' shortcut.
        assert "transport.ssl.verification_mode=certificate" in MAIN

    def test_opensearch_security_and_tls(self):
        assert "plugins.security.disabled=${OPENSEARCH_SECURITY_DISABLED:-false}" in OS_COMPOSE
        assert "plugins.security.ssl.http.enabled=true" in OS_COMPOSE
        assert "plugins.security.ssl.transport.pemcert_filepath" in OS_COMPOSE

    def test_shuffle_tls_verify_defaults_on(self):
        assert 'SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY: "${SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY:-false}"' in CORE
        assert "SHUFFLE_OPENSEARCH_CERTIFICATE_FILE: /certs/ca.crt" in CORE


class TestSegmentation:
    """ISO A.13.1 / CIS 12 — network segmentation and exposure."""

    def test_ti_net_is_internal(self):
        ti_net = MAIN_YML["networks"]["ti_net"]
        assert ti_net.get("internal") is True, (
            "ti_net must stay internal (no egress to the host network)"
        )

    def test_no_public_port_binds(self):
        for name, text in (
            ("docker-compose.yml", MAIN),
            ("docker-compose.core.yml", CORE),
            ("docker-compose.opensearch.yml", OS_COMPOSE),
        ):
            for bind in _published_ports(text):
                assert bind.startswith("127.0.0.1:"), (
                    f"{name}: port binding {bind!r} is not loopback-only"
                )

    def test_soar_net_has_fixed_subnet(self):
        assert "10.100.0.0/16" in MAIN


class TestAvailability:
    """ISO A.12.1 / NIST PR.PS-1 — resilience of every core service."""

    CORE_SERVICES = ("redis", "thehive", "cortex", "shuffle-backend")

    def test_core_services_have_healthcheck_restart_and_limits(self):
        services = CORE_YML["services"]
        missing = {}
        for name in self.CORE_SERVICES:
            svc = services.get(name)
            assert svc, f"{name} missing from docker-compose.core.yml"
            problems = []
            if "healthcheck" not in svc:
                problems.append("healthcheck")
            if svc.get("restart") != "unless-stopped":
                problems.append("restart")
            limits = svc.get("deploy", {}).get("resources", {}).get("limits")
            if not limits:
                problems.append("resource limits")
            log_opts = svc.get("logging", {}).get("options", {})
            if "max-size" not in log_opts:
                problems.append("log rotation")
            if problems:
                missing[name] = problems
        assert not missing, f"core services lacking resilience controls: {missing}"

    def test_elasticsearch_resilience(self):
        es = MAIN_YML["services"].get("elasticsearch")
        assert es, "elasticsearch missing"
        assert "healthcheck" in es
        assert es.get("restart") == "unless-stopped"
        assert es["deploy"]["resources"]["limits"]

    def test_healthchecks_probe_at_app_level(self):
        # Port-open checks (nc -z) alone are not enough for data stores —
        # ES healthcheck must authenticate over TLS.
        assert "--cacert" in MAIN and "_cluster/health" in MAIN


class TestContainerHardening:
    """CIS 4 / NIST PR.PS-3 — hardened-by-default deployment."""

    def test_hardened_overlay_has_cap_drop_all(self):
        assert HARDENED.count("cap_drop") >= 8
        assert "cap_drop: [ALL]" in HARDENED

    def test_no_new_privileges_present(self):
        assert "no-new-privileges:true" in HARDENED or "no-new-privileges" in HARDENED

    def test_read_only_rootfs_used(self):
        assert HARDENED.count("read_only: true") >= 10

    def test_non_root_users(self):
        assert 'user: "redis"' in HARDENED
        assert re.search(r'user: "\$\{API_UID:-1000\}', HARDENED)


class TestCredentials:
    """ISO A.9/A.12.4 / CIS 5 — credential handling."""

    def test_critical_secrets_fail_fast(self):
        assert "CORTEX_API_KEY:?CORTEX_API_KEY required" in CORE
        assert "THEHIVE_SECRET:?THEHIVE_SECRET required" in CORE

    def test_swagger_disabled_by_default(self):
        assert 'SHUFFLE_SWAGGER_ENABLED: "${SHUFFLE_SWAGGER_ENABLED:-false}"' in CORE

    def test_socket_proxy_used_by_api_not_raw_sock(self):
        assert "DOCKER_HOST=tcp://docker-socket-proxy:2375" in HARDENED

    def test_spawners_route_through_socket_proxy(self):
        # SOAR-012 closed under the hardened overlay: cortex / orborus /
        # shuffle-backend get DOCKER_HOST and a `volumes: !override` that
        # drops the raw /var/run/docker.sock mount.
        for svc in ("cortex", "orborus", "shuffle-backend"):
            m = re.search(
                rf"^  {re.escape(svc)}:\n(.*?)(?=^  [a-z0-9_-]+:|\Z)",
                HARDENED,
                re.S | re.M,
            )
            assert m, f"{svc} missing in hardened overlay"
            block = m.group(1)
            assert "DOCKER_HOST=tcp://docker-socket-proxy:2375" in block, svc
            assert "volumes: !override" in block, svc
