"""Architecture gates — MISP (ISO 27001 A.5.7 threat-intelligence, A.8;
NIST SP 800-150 CTI sharing; STIX/TAXII standards).

Invariants for the MISP stack (compose docker-compose.misp.yml) and the
workflow's bidirectional IoC sharing (workflow_actions.py):

- PKI: CA-signed server cert mounted (never the image's self-signed), lab CA
  bundle over the system store so PHP/redis clients verify internal TLS.
- Segmentation: misp-db + misp-modules live ONLY on misp_internal.
- Auth: every MISP credential flows from env; TLS redis scheme required.
- Sharing: workflow must keep both misp_search (inbound enrichment) and
  misp_create (outbound publish with to_ids IDS flag).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MISP_YML = (ROOT / "infra" / "docker" / "compose" / "docker-compose.misp.yml").read_text(
    encoding="utf-8"
)
ACTIONS = (ROOT / "scripts" / "setup" / "shuffle_workflow" / "workflow_actions.py").read_text(
    encoding="utf-8"
)


class TestMispPKI:
    """ISO A.13 / PKI — CA-signed TLS, never self-signed bootstrap."""

    def test_server_cert_is_lab_ca_signed(self):
        assert "certs/misp-full.pem:/etc/nginx/certs/cert.pem:ro" in MISP_YML
        assert "certs/misp.key:/etc/nginx/certs/key.pem:ro" in MISP_YML

    def test_lab_ca_bundle_overrides_system_store(self):
        assert (
            "debian-ca-plus-lab.crt:/etc/ssl/certs/ca-certificates.crt:ro" in MISP_YML
        )

    def test_base_url_is_https(self):
        assert "BASE_URL: https://" in MISP_YML
        # Host port maps the TLS listener, not the :80 redirect hop.
        assert ':443"' in MISP_YML


class TestMispSegmentation:
    """ISO A.8.20/A.13 — backend plane isolated."""

    def test_misp_internal_network_declared(self):
        assert re.search(r"^networks:\n  misp_internal:", MISP_YML, re.M)

    def test_db_and_modules_off_public_net(self):
        # NET-EVAL-2-001: misp-db moved to misp_db_net (internal:true —
        # physically no egress), strictly stronger than misp_internal.
        # The invariant: on a dedicated backend plane, off soar_net.
        for svc, allowed_net in (("misp-db", "misp_db_net"),
                                 ("misp-modules", "misp_internal")):
            m = re.search(
                rf"^  {svc}:\n(.*?)(?=^  [a-z0-9_-]+:|\Z)", MISP_YML, re.S | re.M
            )
            assert m, svc
            block = m.group(1)
            assert re.search(rf"- {allowed_net}", block), svc
            assert re.search(r"- soar_net", block) is None, (
                f"{svc} must not be on soar_net"
            )
            assert re.search(r"^\s+ports:", block, re.M) is None, (
                f"{svc} must not publish host ports"
            )


class TestMispAuthAndCrypto:
    """ISO A.5.17/A.8.24 — credentials + app-layer encryption keys."""

    def test_crypto_keys_come_from_env(self):
        assert "ENCRYPTION_KEY: ${MISP_ENCRYPTION_KEY}" in MISP_YML
        assert "SALT: ${MISP_SALT}" in MISP_YML
        assert "ADMIN_KEY: ${MISP_API_KEY}" in MISP_YML

    def test_redis_scheme_is_tls(self):
        assert 'REDIS_HOST: ${MISP_REDIS_HOST:-tls://redis}' in MISP_YML

    def test_healthcheck_probes_tls_app(self):
        assert '"--cacert"' in MISP_YML and "/users/heartbeat" in MISP_YML


class TestIocSharing:
    """NIST SP 800-150 — bidirectional CTI exchange via the workflow."""

    def test_inbound_enrichment_node_exists(self):
        assert "ACT_MISP = " in ACTIONS
        assert "/attributes/restSearch" in ACTIONS
        # Searches the alert hash across hash types
        assert '"sha256"' in ACTIONS

    def test_outbound_publish_node_exists(self):
        assert "ACT_MISP_CREATE" in ACTIONS
        # Publishes sha256 + ip-dst with the IDS flag — proper CTI semantics
        assert '"to_ids": true' in ACTIONS or "'to_ids': true" in ACTIONS

    def test_misp_calls_use_tls(self):
        assert "https://misp" in ACTIONS or "MISP_INT" in ACTIONS


class TestMispDbSecrets:
    """A.5.17/A.9.4 — db passwords via _FILE, never in `docker inspect`."""

    def test_db_uses_file_secrets(self):
        db = re.search(r"^  misp-db:\n(.*?)(?=^  \w)", MISP_YML, re.S | re.M)
        assert db, "misp-db service block not found"
        block = db.group(1)
        assert "MYSQL_ROOT_PASSWORD_FILE" in block
        assert "MYSQL_PASSWORD_FILE" in block
        # The misp app itself still needs MYSQL_PASSWORD env to connect —
        # that is an upstream limitation; the db container must not.
        assert "MYSQL_ROOT_PASSWORD:" not in block
        assert "MYSQL_PASSWORD:" not in block

    def test_db_secrets_env_sourced(self):
        assert re.search(r"^secrets:\n(?:  \w+:\n    environment: \w+\n?)+", MISP_YML, re.M)
        assert "misp_db_root_password" in MISP_YML and "misp_db_password" in MISP_YML

    def test_healthcheck_reads_secret_file(self):
        assert "$(cat /run/secrets/misp_db_root_password)" in MISP_YML.replace("$$", "$") or \
               "$$(cat /run/secrets/misp_db_root_password)" in MISP_YML


class TestModulesProbe:
    """A.12.1.3 — misp-modules healthcheck is functional, not a socket check."""

    def test_healthcheck_runs_real_query(self):
        svc = re.search(r"misp-modules:\n(.*?)(?=^  \w|\Z)", MISP_YML, re.S | re.M)
        assert svc and "/query" in svc.group(1), "probe must POST /query"
        assert "socket.socket" not in svc.group(1)


class TestLeastPrivilege:
    """A.8.2/A.9 — integration uses a Publisher key, admin only for bootstrap."""

    def test_api_prefers_automation_key(self):
        api_yml = (ROOT / "infra" / "docker" / "compose" / "docker-compose.api.yml").read_text(
            encoding="utf-8"
        )
        assert "MISP_AUTOMATION_API_KEY" in api_yml

    def test_taxonomy_refresh_script_exists(self):
        assert (
            ROOT / "scripts" / "maintenance" / "misp_update_taxonomies.py"
        ).is_file()
