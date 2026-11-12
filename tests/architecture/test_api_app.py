"""Custom API (FastAPI app) regression gates (docs/32-eval-api.md).

API-EVAL findings pinned as gates:
  API-EVAL-001 PreAuthRateLimit must be OUTER of DefaultDenyAuth —
               Starlette's last-added middleware is outermost; the
               registration order in main._add_middlewares decides.
  API-EVAL-002 `server: uvicorn` banner suppressed at the protocol
               layer (--no-server-header in the image CMD) — the
               middleware-level `del` cannot reach it.
  API-EVAL-003 UVICORN_WORKERS>1 with memory backends must not boot —
               composition fails closed on the fragmented-state misconfig.
Positive gates: default-deny middleware, scoped service tokens, body
limit, security headers, trace id, hardened container posture.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "src" / "soar_lab" / "interfaces" / "api" / "main.py"
AUTH = ROOT / "src" / "soar_lab" / "interfaces" / "api" / "auth.py"
COMPOSITION = ROOT / "src" / "soar_lab" / "interfaces" / "api" / "composition.py"
DOCKERFILE = ROOT / "apps" / "api" / "Dockerfile"
API_COMPOSE = ROOT / "infra" / "docker" / "compose" / "docker-compose.api.yml"
HARDENED = ROOT / "infra" / "docker" / "compose" / "docker-compose.hardened.yml"


class _Loader(yaml.SafeLoader):
    """Tolerate compose-spec tags (!reset / !override)."""


def _tag(loader, suffix, node):
    if suffix == "override":
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
    return None


_Loader.add_multi_constructor("!", _tag)


def _load(p: Path):
    return yaml.load(p.read_text(encoding="utf-8"), Loader=_Loader)


class _FakeCp:
    """Minimal config provider for _add_middlewares."""

    def get(self, key, default=None):
        return default


def _middleware_order() -> list[str]:
    from soar_lab.interfaces.api.main import _add_middlewares

    app = FastAPI()
    _add_middlewares(app, _FakeCp())
    return [m.cls.__name__ for m in app.user_middleware]


def test_preauth_limiter_is_outer_of_default_deny():
    """API-EVAL-001: brute-force auth attempts must consume IP budget.

    user_middleware[0] is outermost — PreAuthRateLimitMiddleware must
    precede DefaultDenyAuthMiddleware or failed auth is never limited.
    """
    order = _middleware_order()
    assert "PreAuthRateLimitMiddleware" in order
    assert "DefaultDenyAuthMiddleware" in order
    assert order.index("PreAuthRateLimitMiddleware") < order.index(
        "DefaultDenyAuthMiddleware"
    ), f"middleware order regressed: {order}"


def test_trace_id_is_outermost():
    """Every response incl. 401/429 must carry X-Request-ID."""
    assert _middleware_order()[0] == "TraceIdMiddleware"


def test_security_headers_wrap_everything_but_trace():
    """SecurityHeaders second-outermost: covers 401/403/429/500 bodies."""
    assert _middleware_order()[1] == "SecurityHeadersMiddleware"


def test_body_limit_before_auth():
    """DOS-001: oversized bodies rejected before auth parse."""
    order = _middleware_order()
    assert order.index("BodyLimitMiddleware") < order.index("DefaultDenyAuthMiddleware")


def test_dockerfile_disables_server_header():
    """API-EVAL-002: protocol-layer banner off — middleware can't reach it."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "--no-server-header" in text


def test_composition_rejects_workers_with_memory_backends():
    """API-EVAL-003: fail-closed coherence guard must exist in code."""
    text = COMPOSITION.read_text(encoding="utf-8")
    assert "UVICORN_WORKERS" in text and "RuntimeError" in text
    assert "RATE_LIMIT_BACKEND" in text and "WS_TICKET_BACKEND" in text


def test_service_token_scopes_are_least_privilege():
    """Every scope except break-glass internal has explicit route rules."""
    text = AUTH.read_text(encoding="utf-8")
    for scope in ("webhook", "containment", "cache", "callback", "metrics"):
        assert f'"{scope}"' in text, f"scope '{scope}' missing"
    # internal documented as break-glass unrestricted
    assert '"internal": ()' in text


def test_public_whitelist_is_minimal():
    """PUBLIC_PREFIXES holds only probes/docs/auth — nothing else."""
    text = AUTH.read_text(encoding="utf-8")
    m = re.search(r"PUBLIC_PREFIXES[^=]*=\s*\((.*?)\)", text, re.S)
    assert m, "PUBLIC_PREFIXES not found"
    entries = re.findall(r'"([^"]+)"', m.group(1))
    assert set(entries) == {
        "/health", "/metrics", "/docs", "/redoc", "/openapi.json",
        "/auth/", "/api/v1/auth/", "/static", "/favicon",
    }


def test_api_service_hardened_posture():
    """Container: non-root, cap_drop, nnp, pids, loopback-bound port."""
    api = _load(API_COMPOSE)
    hard = _load(HARDENED)
    svc = api["services"]["api"]
    hsvc = hard["services"]["api"]
    ports = svc.get("ports") or []
    assert ports and all(str(p).startswith("127.0.0.1") or "127.0.0.1:" in str(p) for p in ports)
    assert hsvc.get("user"), "hardened api lacks non-root user"
    assert "ALL" in (hsvc.get("cap_drop") or [])
    assert any("no-new-privileges" in o for o in (hsvc.get("security_opt") or []))
    limits = hsvc.get("deploy", {}).get("resources", {}).get("limits", {})
    assert limits.get("pids"), "hardened api lacks pids limit"
