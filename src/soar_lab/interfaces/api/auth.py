"""Authentication adapter for SOAR Lab API.

This module acts as a FastAPI adapter for the AuthService, delegating
authentication logic to the service layer.
"""

import hashlib
import hmac
import ipaddress
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from soar_lab.auth.models import Role, User
from soar_lab.common.exceptions import AuthError
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()
_optional_security = HTTPBearer(auto_error=False)

SERVICE_TOKEN_HEADER = "X-Service-Token"  # pragma: allowlist secret
SERVICE_TOKEN_AUTH_SCHEME = "service-token"  # Authorization: Service-Token <tok>


def create_get_current_user(auth_service) -> object:
    """Factory that creates a get_current_user dependency with injected.

    auth_service.

    Args:
        auth_service: AuthService instance (injected dependency)

    Returns:
        FastAPI dependency function for authentication
    """
    if not auth_service:
        raise ValueError("auth_service is required for create_get_current_user")

    def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict[str, Any]:
        """Verify JWT token and return user information.

        Delegates to AuthService for actual authentication logic.
        """
        logger.info("get_current_user called")
        token = credentials.credentials
        if token:
            fp = hashlib.sha256(token.encode()).hexdigest()[:12]
            logger.info(f"Token received (sha256 fp={fp})")

        try:
            user_info = auth_service.verify_jwt_token(token)
            logger.info(f"User authenticated: {user_info.get('user', 'unknown')}")
            return user_info
        except AuthError as e:
            logger.warning(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"} if e.status_code == 401 else None,
            ) from e

    return get_current_user


def _auth_required(config_provider: Any) -> bool:
    """Return True when API_REQUIRE_AUTH enables endpoint enforcement.

    Secure by default: auth is ON unless the operator explicitly opts out
    with ``API_REQUIRE_AUTH=false``.
    """
    value = str(config_provider.get("API_REQUIRE_AUTH", "true")).lower()
    return value not in ("0", "false", "off", "no")


# AUTH-002: least-privilege service identities. Each env-var maps a
# distinct credential to a narrow scope; "internal" stays the break-glass
# full-access identity (NOT embedded in workflow definitions anymore).
_SERVICE_TOKEN_SCOPES: tuple[tuple[str, str], ...] = (
    ("INTERNAL_SERVICE_TOKEN", "internal"),
    ("SHUFFLE_WEBHOOK_TOKEN", "webhook"),
    ("CONTAINMENT_SERVICE_TOKEN", "containment"),
    ("CACHE_SERVICE_TOKEN", "cache"),
    ("CALLBACK_SERVICE_TOKEN", "callback"),
    ("METRICS_SERVICE_TOKEN", "metrics"),
)
_SERVICE_TOKEN_PREV_SCOPES: tuple[tuple[str, str], ...] = tuple(
    (f"{k}_PREV", sc) for k, sc in _SERVICE_TOKEN_SCOPES
)

# scope -> allowed (method, path) rules. A rule matches when method is
# equal AND (path == rule or path.startswith(rule + "/")).
_SCOPE_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "internal": (),  # empty = unrestricted (break-glass only)
    "webhook": (
        ("POST", "/api/v1/alerts"),          # exact: ingest only
        ("POST", "/api/v1/alerts/grafana"),  # exact: grafana receiver
        ("GET", "/api/v1/alerts/"),          # prefix: admission status
    ),
    "callback": (("POST", "/api/v1/alerts/callback"),),
    "containment": (("POST", "/api/v1/contain"),),
    "cache": (
        ("GET", "/api/v1/cache"),
        ("GET", "/api/v1/cache/"),
        ("POST", "/api/v1/cache"),
        ("POST", "/api/v1/cache/"),
    ),
    "metrics": (("GET", "/metrics"),),
}


def _cred_fp(token_b: bytes) -> str:
    """AUTH-005: irreversible credential fingerprint for audit/identity."""
    return hashlib.sha256(token_b).hexdigest()[:12]


def _scope_allowed(scope: str, method: str, path: str) -> bool:
    rules = _SCOPE_RULES.get(scope)
    if rules is None:
        return False  # unknown scope -> deny
    if not rules:
        return True  # internal break-glass
    m = method.upper()
    for rm, rp in rules:
        if m != rm:
            continue
        # Rules ending in "/" are prefix rules; otherwise exact match.
        # (keeps /api/v1/alerts/callback out of the webhook scope.)
        if path == rp or (rp.endswith("/") and path.startswith(rp)):
            return True
    return False


def _service_token_scope(request: Request, config_provider: Any) -> tuple[str | None, bool, str | None]:
    """Resolve the X-Service-Token header to ``(scope, rotation_grace)``.

    ``INTERNAL_SERVICE_TOKEN`` grants the full ``internal`` scope. The
    ``SHUFFLE_WEBHOOK_TOKEN`` lab fallback is scoped to ``webhook`` — it is
    embedded in workflow definitions (widely distributed), so it must not
    carry the same privileges as the internal token.

    S2 token rotation: each token has an optional ``*_PREV`` slot
    (``INTERNAL_SERVICE_TOKEN_PREV``, ``SHUFFLE_WEBHOOK_TOKEN_PREV``).
    During rotation the previous secret stays accepted so in-flight
    workflows don't break; ``rotation_grace`` reports that the old
    secret authenticated so the audit trail exposes callers still on
    the stale credential.
    """
    token = request.headers.get(SERVICE_TOKEN_HEADER)
    if not token:
        # GRAF-ALERT-RX: Grafana's webhook sender cannot attach arbitrary
        # headers, but it natively supports ``Authorization: <scheme>
        # <credentials>``. ``Service-Token`` is accepted as an equivalent
        # transport for the same shared secret (non-Bearer schemes pass
        # HTTPBearer(auto_error=False) as ``None`` credentials).
        authz = request.headers.get("Authorization", "")
        scheme, _, credential = authz.partition(" ")
        if scheme.lower() == SERVICE_TOKEN_AUTH_SCHEME and credential.strip():
            token = credential.strip()
    if not token:
        return None, False, None
    token_b = token.encode("utf-8")
    for key, scope in _SERVICE_TOKEN_SCOPES:
        accepted = config_provider.get(key)
        if accepted and hmac.compare_digest(token_b, str(accepted).encode("utf-8")):
            return scope, False, _cred_fp(token_b)
    for key, scope in _SERVICE_TOKEN_PREV_SCOPES:
        accepted = config_provider.get(key)
        if accepted and hmac.compare_digest(token_b, str(accepted).encode("utf-8")):
            return scope, True, _cred_fp(token_b)
    return None, False, None


# Webhook scope reaches alert ingest + admission status only — not DLQ
# admin, audit, config dump or containment, which stay internal-only.
_WEBHOOK_SCOPE_PREFIX = "/api/v1/alerts"


def _webhook_cidr_allowed(request: Request, config_provider: Any) -> bool:
    """S5: optional source-IP allowlist for the webhook-scope token.

    ``WEBHOOK_ALLOW_CIDRS`` is a comma-separated CIDR list (e.g.
    ``172.16.0.0/12``). When set, the webhook token is only honored from
    those networks — the token embedded in Shuffle workflows cannot be
    replayed from an arbitrary host. Empty/unset disables the check
    (lab default).
    """
    raw = str(
        config_provider.get("SERVICE_TOKEN_ALLOW_CIDRS")
        or config_provider.get("WEBHOOK_ALLOW_CIDRS")
        or ""
    ).strip()
    if not raw:
        return True
    client_ip = request.client.host if request.client else None
    try:
        # `ip_address(None)` raises TypeError (not ValueError) — coerce to ""
        # so a missing client address takes the same deny path as a bad one.
        ip = ipaddress.ip_address(client_ip or "")
    except ValueError:
        return False
    for cidr in raw.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            logger.warning("Ignoring invalid WEBHOOK_ALLOW_CIDRS entry: %s", cidr)
    return False


def _audit_access(
    request: Request,
    *,
    principal: str,
    result: str,
    detail: str = "",
) -> None:
    """AUTH-004: append one record to the bounded auth audit trail.

    Covers user/endpoint/method/result per authenticated request; denials
    (401/403) are recorded too so the trail shows attacks, not just usage.
    """
    svc = getattr(request.app.state, "auth_service", None)
    audit = getattr(svc, "audit", None)
    if audit is None:
        return
    try:
        audit.record(
            "access",
            principal=principal,
            endpoint=request.url.path,
            method=request.method,
            result=result,
            detail=detail,
        )
    except Exception:
        logger.debug("audit record failed", exc_info=True)


def _principal_name(principal: dict[str, Any]) -> str:
    return str(principal.get("user") or principal.get("service") or principal.get("sub") or "?")


def _enforce_role(request: Request, principal: dict[str, Any]) -> None:
    """AUTH-003: role-based authorization after authentication.

    JWT principals carry a ``role`` claim (``WEB_UI_ROLE`` at login).
    Service tokens are internal machine accounts → full access. A missing
    claim means a legacy token → treated as admin for backwards
    compatibility; an *unknown* claim value falls back to read-only.
    """
    if principal.get("service"):
        return
    role_claim = principal.get("role")
    if role_claim is None:
        # AUTH-004: a JWT without a role claim is legacy — read-only,
        # never admin. Deny-by-default for anything mutating.
        role_claim = Role.READONLY.value
    svc = getattr(request.app.state, "auth_service", None)
    if svc is None:
        return

    try:
        role = Role(str(role_claim))
    except ValueError:
        role = Role.READONLY
    user = User(
        id=_principal_name(principal),
        username=_principal_name(principal),
        role=role,
    )
    if not svc.can_access_endpoint(user, request.url.path, request.method):
        _audit_access(
            request,
            principal=user.username,
            result="deny",
            detail=f"role={role.value} {request.method} {request.url.path}",
        )
        logger.warning(
            "RBAC deny user=%s role=%s %s %s",
            user.username,
            role.value,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=403, detail="Insufficient role for this endpoint")


async def require_api_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_security),
) -> dict[str, Any]:
    """Gate mutating endpoints behind JWT or a shared service token.

    Enabled by default (``API_REQUIRE_AUTH=true``); set it explicitly to
    ``false`` only for throwaway lab runs:

    - Browser/web-management calls authenticate with the existing JWT.
    - Internal services (e.g. the Shuffle workflow) authenticate with the
      ``X-Service-Token`` header matching ``INTERNAL_SERVICE_TOKEN`` (or the
      Shuffle webhook token as a lab fallback).

    The resolved principal is cached on ``request.state`` so the
    DefaultDenyAuthMiddleware → route Depends() chain audits and
    authorizes exactly once per request.
    """
    cached = getattr(request.state, "_auth_principal", None)
    if cached is not None:
        return cached

    cp = request.app.state.config_provider
    if cp is None or not _auth_required(cp):
        if not getattr(request.app.state, "_auth_off_warned", False):
            request.app.state._auth_off_warned = True
            logger.warning(
                "API_REQUIRE_AUTH is OFF - mutating endpoints accept "
                "unauthenticated requests. Set API_REQUIRE_AUTH=true."
            )
        principal = {"user": "unauthenticated-allowed"}
        request.state._auth_principal = principal
        return principal

    token_scope, rotation_grace, cred_fp = _service_token_scope(request, cp)
    if token_scope:
        return _service_token_principal(request, cp, token_scope, rotation_grace, cred_fp)

    if credentials is not None:
        principal = _jwt_principal(request, credentials)
        if principal is not None:
            return principal

    _audit_access(request, principal="anonymous", result="deny", detail="no credentials")
    raise HTTPException(
        status_code=401,
        detail="Authentication required: Bearer JWT or X-Service-Token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _service_token_principal(
    request: Request,
    cp: Any,
    token_scope: str,
    rotation_grace: bool,
    cred_fp: str | None = None,
) -> dict[str, Any]:
    # AUTH-002: every service token is confined to its scope rules and
    # honours the CIDR allowlist — not only the webhook scope.
    if not _webhook_cidr_allowed(request, cp):
        _audit_access(
            request,
            principal=f"service:{token_scope}",
            result="deny",
            detail=f"cidr-blocked src={request.client.host if request.client else '?'}",
        )
        raise HTTPException(status_code=403, detail="Service token source not allowed")
    if not _scope_allowed(token_scope, request.method, request.url.path):
        _audit_access(
            request,
            principal=f"service:{token_scope}",
            result="deny",
            detail=f"scope={token_scope} {request.method} {request.url.path}",
        )
        raise HTTPException(status_code=403, detail=f"Token scope {token_scope} denied")
    principal = {"service": token_scope, "credential_id": cred_fp}
    request.state._auth_principal = principal
    _audit_access(
        request,
        principal=f"service:{token_scope}",
        result="allow",
        detail="rotation-grace" if rotation_grace else "",
    )
    if rotation_grace:
        # nosemgrep: python-logger-credential-disclosure -- metadata only
        logger.warning(
            "service token rotation grace in use scope=%s path=%s — "
            "rotate callers off the *_PREV secret",
            token_scope,
            request.url.path,
        )
    return principal


def _jwt_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials,
) -> dict[str, Any] | None:
    get_current_user = request.app.state.get_current_user
    if get_current_user is None:
        return None
    try:
        principal = get_current_user(credentials)
    except HTTPException:
        _audit_access(request, principal="anonymous", result="deny", detail="invalid jwt")
        raise
    request.state._auth_principal = principal
    _enforce_role(request, principal)
    _audit_access(request, principal=_principal_name(principal), result="allow")
    return principal


class DefaultDenyAuthMiddleware:
    """AUTH-001: default-deny authentication for the whole API surface.

    Pure-ASGI middleware (no ``BaseHTTPMiddleware`` buffering). Every
    HTTP route outside the explicit public whitelist must satisfy
    :func:`require_api_auth` — the same gate per-route ``Depends`` uses.
    Because it wraps routing, any FUTURE route added without an auth
    dependency is still protected: security posture cannot silently
    regress when a developer forgets ``Depends(require_api_auth)``.

    Public whitelist (probes, docs, auth endpoints themselves, WS —
    WebSockets use a separate scope and the one-time ticket gate):
    ``/health``, ``/metrics``, ``/docs``, ``/redoc``, ``/openapi.json``,
    ``/auth/*``, ``/static*``, ``/`` and CORS preflights.
    """

    PUBLIC_PREFIXES: tuple[str, ...] = (
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/",
        "/api/v1/auth/",
        "/static",
        "/favicon",
    )

    def __init__(self, app: Any) -> None:
        self.app = app

    def _is_public(self, path: str, method: str) -> bool:
        if method == "OPTIONS":  # CORS preflight — handled by CORSMiddleware
            return True
        return path == "/" or path.startswith(self.PUBLIC_PREFIXES)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        if self._is_public(path, method):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        credentials = None
        authz = request.headers.get("authorization", "")
        if authz.lower().startswith("bearer "):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=authz[7:].strip()
            )
        try:
            await require_api_auth(request, credentials)
        except HTTPException as exc:

            response = JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers=getattr(exc, "headers", None),
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
