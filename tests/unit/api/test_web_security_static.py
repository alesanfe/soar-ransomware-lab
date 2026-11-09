#!/usr/bin/env python3
"""Static regressions for web-layer hardening (WEB-CORS-001, WEB-TLS-001,
WEB-TLS-006). Source-file assertions — no Docker required."""

import re
from pathlib import Path

# Locate the repo root by walking up until infra/docker is found — under
# mutation testing the tests run from a copied tree (mutants/) without infra/.
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "infra/docker").is_dir())
NGINX = ROOT / "infra/docker/config/nginx/nginx.conf"
COMPOSE_API = ROOT / "infra/docker/compose/docker-compose.api.yml"
GITIGNORE = ROOT / ".gitignore"


class TestNginxCors:
    def test_no_reflective_origin(self):
        conf = NGINX.read_text(encoding="utf-8")
        # Every ACAO header must come from the allowlist map, never the
        # raw $http_origin variable (that would reflect any attacker origin).
        for line in conf.splitlines():
            if "Access-Control-Allow-Origin" in line and "add_header" in line:
                assert "$cors_allow_origin" in line
                assert "$http_origin" not in line

    def test_allowlist_map_exists(self):
        conf = NGINX.read_text(encoding="utf-8")
        assert "map $http_origin $cors_allow_origin" in conf

    def test_no_wildcard_origin(self):
        conf = NGINX.read_text(encoding="utf-8")
        assert 'Access-Control-Allow-Origin "*"' not in conf


class TestNginxUpstreamWiring:
    """WEB-PROXY-001: `set $upstream` must precede `rewrite ... break` —
    `break` stops rewrite-module processing, so a `set` placed after it
    never runs and proxy_pass sees an empty upstream (500).

    WEB-PROXY-002: `/api/v1/*` routes are registered in FastAPI WITH the
    /api prefix, so they need a location that proxies them unmodified —
    the generic /api/ block strips the prefix and produces 404s.
    """

    @staticmethod
    def _blocks(conf: str) -> list[str]:
        # Split into `location X { ... }` bodies (flat — no nested braces
        # in this config).
        return re.findall(r"location\s+\S+\s*\{([^}]*)\}", conf)

    def test_set_upstream_before_rewrite_break(self):
        conf = NGINX.read_text(encoding="utf-8")
        for body in self._blocks(conf):
            m = re.search(r"proxy_pass\s+http://\$(\w+)", body)
            if not m:
                continue
            var = m.group(1)
            set_pos = body.find(f"set ${var}")
            break_pos = body.find(" break;")
            assert set_pos != -1, f"proxy_pass uses ${var} but no set directive"
            if break_pos != -1:
                assert set_pos < break_pos, (
                    f"`set ${var}` must precede `rewrite ... break` — "
                    "break aborts rewrite-module processing"
                )

    def test_api_v1_passthrough_location(self):
        conf = NGINX.read_text(encoding="utf-8")
        m = re.search(r"location\s+/api/v1/\s*\{([^}]*)\}", conf)
        assert m is not None, "missing /api/v1/ passthrough location"
        body = m.group(1)
        assert "rewrite" not in body, (
            "/api/v1/ must proxy unmodified — FastAPI registers these "
            "routes with the /api prefix"
        )


class TestTlsArtifacts:
    def test_private_keys_not_tracked_patterns(self):
        import pytest

        if not GITIGNORE.exists():
            pytest.skip(".gitignore not present in this checkout (e.g. mutants/ tree)")
        gi = GITIGNORE.read_text(encoding="utf-8")
        for pat in ("*.key", "*.pfx", "*.p12"):
            assert re.search(rf"^{re.escape(pat)}\s*$", gi, re.MULTILINE), pat

    def test_ssl_dir_has_no_pfx(self):
        ssl = ROOT / "infra/docker/config/nginx/ssl"
        assert not list(ssl.glob("*.pfx")), "PFX bundle must not be committed"


class TestPortExposure:
    def test_api_port_loopback_only(self):
        text = COMPOSE_API.read_text(encoding="utf-8")
        # Scope to the `api:` service block (file holds multiple services).
        block = re.search(r"^\s{2}api:\n(.*?)(?=^\s{2}\S)", text, re.DOTALL | re.MULTILINE)
        assert block is not None
        body = block.group(1)
        assert (
            '"127.0.0.1:${API_PORT' in body
        ), "API must bind to loopback only — nginx is the public edge"
        assert not re.search(r'-\s*"\$\{API_PORT', body)
