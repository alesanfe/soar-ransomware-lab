"""Architecture gates — TAXII (ISO 27001 A.5.7/A.8; NIST SP 800-150 CTI;
STIX 2.1 / TAXII 2.1 standards).

Two surfaces, both covered:

- ``soar_taxii`` (medallion) — ti_net-only feed endpoint, creds injected at
  start, most-hardened container in the stack.
- TAXII-lite — FastAPI surface over the STIX 2.1 export (ADR-0011 scope):
  authenticated, honest ``more`` flag, read-only collection.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAXII_YML = (ROOT / "infra" / "docker" / "compose" / "docker-compose.taxii.yml").read_text(
    encoding="utf-8"
)
ROUTES = (ROOT / "src" / "soar_lab" / "interfaces" / "api" / "routes_taxii.py").read_text(
    encoding="utf-8"
)
SERVER = (ROOT / "src" / "soar_lab" / "application" / "use_cases" / "taxii_server.py").read_text(
    encoding="utf-8"
)
STIX = (ROOT / "src" / "soar_lab" / "application" / "use_cases" / "stix_export.py").read_text(
    encoding="utf-8"
)
MEDALLION_CFG = (ROOT / "infra" / "docker" / "taxii" / "config.json").read_text(
    encoding="utf-8"
)


class TestMedallionHardening:
    """A.8.20/A.5.17 — the feed container is internal-only + locked down."""

    def test_ti_net_only_no_published_ports(self):
        svc = re.search(
            r"^  taxii:\n(.*?)(?=^networks:|\Z)", TAXII_YML, re.S | re.M
        )
        assert svc
        block = svc.group(1)
        assert "- ti_net" in block
        assert re.search(r"^\s+ports:", block, re.M) is None, (
            "taxii must not publish host ports — ti_net only"
        )

    def test_container_hardening(self):
        for directive in ("cap_drop: [ALL]", "no-new-privileges", "read_only: true"):
            assert directive in TAXII_YML, directive
        assert "/tmp:size=" in TAXII_YML  # tmpfs for rendered config

    def test_credentials_injected_not_baked(self):
        assert "TAXII_READER_PASS: ${TAXII_READER_PASS}" in TAXII_YML
        assert "TAXII_WRITER_PASS: ${TAXII_WRITER_PASS}" in TAXII_YML
        # The committed config carries placeholders, never literals.
        assert "__TAXII_READER_PASS__" in MEDALLION_CFG
        assert "__TAXII_WRITER_PASS__" in MEDALLION_CFG

    def test_app_level_healthcheck(self):
        assert "/taxii2/" in TAXII_YML and "200,401" in TAXII_YML


class TestTaxiiLiteAuth:
    """A.5.17 — every lite endpoint requires API auth."""

    def test_all_endpoints_authenticated(self):
        routes = re.findall(r"@app_instance\.get\((.*?)\)", ROUTES, re.S)
        assert len(routes) == 6, "expected 6 TAXII-lite routes"
        for r in routes:
            assert "_AUTH" in r, f"unauthenticated TAXII route: {r[:80]}"

    def test_taxii_media_type_on_objects(self):
        assert '"application/taxii+json;version=2.1"' in ROUTES
        assert "media_type=_TAXII_MEDIA" in ROUTES


class TestTaxiiLiteSemantics:
    """STIX/TAXII standards — the lite surface stays honest about scope."""

    def test_read_only_collection(self):
        assert '"can_read": True' in SERVER
        assert '"can_write": False' in SERVER
        assert '"versions": [_TAXII_VERSION]' in SERVER

    def test_honest_more_flag(self):
        # `more` must only be true when truncation actually happened —
        # the +1 probe compares object counts, never a guess.
        assert "bounded + 1" in SERVER
        assert "more = len(probe" in SERVER

    def test_limit_bounded(self):
        assert "min(limit, 10_000)" in SERVER

    def test_collection_id_stable_uuid5(self):
        assert 'uuid.uuid5(STIX_NS, "taxii-collection:lab-alerts")' in SERVER


class TestStixQuality:
    """STIX 2.1 — valid objects, deterministic ids, real patterns."""

    def test_spec_version_and_deterministic_ids(self):
        assert 'STIX_SPEC_VERSION = "2.1"' in STIX
        assert "uuid.uuid5(STIX_NS" in STIX

    def test_valid_stix_patterns(self):
        assert "[file:hashes.'SHA-256' = '" in STIX
        assert "[ipv4-addr:value = '" in STIX
        assert "[domain-name:value = '" in STIX
        assert '"pattern_type": "stix"' in STIX

    def test_provenance_fields(self):
        assert '"created_by_ref"' in STIX
        assert '"identity_class": "system"' in STIX
        assert '"valid_from"' in STIX

    def test_dedup_and_refs(self):
        assert "seen_ids" in STIX
        assert '"object_refs": indicator_refs' in STIX


class TestMedallionTLS:
    """A.8.24 — medallion is TLS-only via gunicorn + lab PKI (TAXII-EVAL-005)."""

    def test_dockerfile_serves_gunicorn(self):
        df = (ROOT / "infra" / "docker" / "taxii" / "Dockerfile").read_text(encoding="utf-8")
        assert "gunicorn" in df, "medallion must be served by gunicorn for TLS"
        assert "tls_app.py" in df

    def test_entrypoint_terminates_tls(self):
        ep = (ROOT / "infra" / "docker" / "taxii" / "entrypoint.sh").read_text(encoding="utf-8")
        assert "--certfile" in ep and "--keyfile" in ep
        assert "exec medallion" not in ep, "plain-HTTP medallion runner must not be used"

    def test_compose_mounts_cert_and_ca(self):
        assert "certs/taxii.crt" in TAXII_YML and "certs/taxii.key" in TAXII_YML
        assert "certs/ca.crt" in TAXII_YML

    def test_healthcheck_uses_https(self):
        assert "HTTPSConnection" in TAXII_YML, "healthcheck must probe TLS, not HTTP"
        assert "HTTPConnection(" not in TAXII_YML.replace("HTTPSConnection(", "")


class TestLiteManifest:
    """TAXII 2.1 spec — read collections expose a manifest resource."""

    def test_manifest_route_registered(self):
        assert re.search(r'collections/\{collection_id\}/manifest/', ROUTES)

    def test_manifest_shape(self):
        for field in ("date_added", "version", "media_type"):
            assert f'"{field}"' in SERVER, f"manifest entry must carry {field}"


class TestStixMarkings:
    """STIX 2.1 quality — objects carry TLP marking + confidence."""

    def test_tlp_marking_emitted(self):
        assert "marking-definition" in STIX
        assert '"tlp": "clear"' in STIX or "'tlp': 'clear'" in STIX

    def test_indicators_carry_confidence_and_marking(self):
        assert '"confidence": 80' in STIX
        assert '"object_marking_refs"' in STIX
