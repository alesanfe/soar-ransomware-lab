"""Authentication Service for SOAR Lab.

This service contains authentication and authorization logic as a use
case, separated from the FastAPI adapter layer.
"""

import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from soar_lab.auth.models import Permission, Role
from soar_lab.common.constants import JWT_ALGORITHM_DEFAULT
from soar_lab.common.exceptions import AuthError
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import ConfigProvider, TokenProviderInterface

logger = get_logger(__name__)


@dataclass
class PermissionGrant:
    """Time-boxed permission grant (SEC-002)."""

    permission: Any
    granted_at: float
    expires_at: float
    granted_by: str = ""


@dataclass
class _AuthAudit:
    """In-memory auth audit trail (SEC-006-lite) — bounded, per-service.

    S6: every record is chained to the previous one —
    ``hash = sha256(prev_hash + canonical(event))`` — so editing or
    deleting a past event breaks every subsequent hash. ``verify()``
    recomputes the chain; ``chain_tip`` is the external attestation
    value a SIEM can snapshot periodically.
    """

    events: list[dict] = field(default_factory=list)
    _max: int = 1000
    _tip: str = "0" * 64

    def record(self, action: str, **kv: Any) -> None:
        body = {"ts": time.time(), "action": action} | kv
        digest = hashlib.sha256(
            self._tip.encode() + json.dumps(body, sort_keys=True, default=str).encode()
        ).hexdigest()
        event = body | {"prev_hash": self._tip, "hash": digest}
        self._tip = digest
        self.events.append(event)
        if len(self.events) > self._max:
            # Trimming keeps the chain verifiable from its new head:
            # the first retained event's prev_hash anchors the rest.
            del self.events[: len(self.events) - self._max]

    @property
    def chain_tip(self) -> str:
        """Current chain head — snapshot this externally to attest the trail."""
        return self._tip

    def verify(self) -> bool:
        """Recompute the chain over retained events; False on tamper."""
        expected_prev = self.events[0]["prev_hash"] if self.events else "0" * 64
        for event in self.events:
            body = {k: v for k, v in event.items() if k not in ("prev_hash", "hash")}
            if event.get("prev_hash") != expected_prev:
                return False
            recomputed = hashlib.sha256(
                expected_prev.encode() + json.dumps(body, sort_keys=True, default=str).encode()
            ).hexdigest()
            if event.get("hash") != recomputed:
                return False
            expected_prev = recomputed
        return True


# Factory callables injected by the composition root.  Using callables
# (instead of direct imports) keeps the application layer free of
# infrastructure dependencies — the factories themselves live in
# ``soar_lab.infrastructure.auth_defaults`` and are wired up by the
# composition root at startup.
_default_config_factory: Callable[[], Any] | None = None
_default_token_factory: Callable[[], TokenProviderInterface] | None = None


def set_default_factories(
    config_factory: Callable[[], Any] | None = None,
    token_factory: Callable[[], TokenProviderInterface] | None = None,
) -> None:
    """Register default provider factories.

    Called by the composition root (infrastructure layer) to inject
    concrete factories without the application layer importing
    infrastructure directly.
    """
    global _default_config_factory, _default_token_factory
    if config_factory is not None:
        _default_config_factory = config_factory
    if token_factory is not None:
        _default_token_factory = token_factory


class AuthService:
    """Service for authentication and authorization operations."""

    def __init__(
        self,
        config_provider: ConfigProvider | None = ...,
        token_provider: TokenProviderInterface | None = ...,
    ) -> None:
        """Initialize the authentication service.

        Args:
            config_provider: Configuration provider for auth settings.
            token_provider: Token provider for JWT operations.
        """
        if config_provider is None:
            raise ValueError("config_provider is required")
        if token_provider is None:
            raise ValueError("token_provider is required")
        if config_provider is ...:
            if _default_config_factory is None:
                raise ValueError(
                    "No default config factory registered. "
                    "Call set_default_factories() from the composition root."
                )
            config_provider = _default_config_factory()
        if token_provider is ...:
            if _default_token_factory is None:
                raise ValueError(
                    "No default token factory registered. "
                    "Call set_default_factories() from the composition root."
                )
            token_provider = _default_token_factory()
        self.config_provider = config_provider
        self.token_provider = token_provider
        self.audit = _AuthAudit()

    def _get_auth_secret(self) -> str:
        """Get authentication secret from ConfigProvider."""
        return (
            self.config_provider.get("jwt_secret_key")
            or self.config_provider.get("api_auth_secret")
            or ""
        )

    def _validate_secret_length(self, secret: str) -> None:
        """Enforce minimum length on the EFFECTIVE secret (SEC-001).

        Previous code skipped the check whenever ``api_auth_secret`` was
        set — a 5-char legacy secret silently bypassed validation. The
        effective secret (jwt_secret_key or api_auth_secret fallback) must
        always be >= 32 chars, whoever provided it.
        """
        if len(secret) < 32:
            raise AuthError("Authentication system not properly configured", 500)

    # ------------------------------------------------------------------
    # RBAC helpers
    # ------------------------------------------------------------------
    def _is_admin(self, user: Any) -> bool:
        """Check whether the user has the ADMIN role.

        Args:
            user: User object with a ``role`` attribute.

        Returns:
            True if the user's role is ADMIN.
        """
        return getattr(user, "role", None) == Role.ADMIN

    def has_permission(self, user: Any, permission: Any) -> bool:
        """Return True if the user has the requested permission.

        Considers permanent permissions plus non-expired temporary grants
        (SEC-002). Expired grants are pruned and never authorize.
        """
        if self._is_admin(user):
            return True
        user_perms = set(getattr(user, "permissions", []))
        if Permission.ALL in user_perms or permission in user_perms:
            return True
        # Temporary grants (SEC-002)
        now = time.time()
        grants = getattr(user, "temp_permissions", []) or []
        live = [g for g in grants if g.expires_at > now]
        if len(live) != len(grants):  # prune expired
            user.temp_permissions = live
        return any(g.permission in (permission, Permission.ALL) for g in live)

    def check_permission(self, user: Any, permission: Any) -> None:
        """Raise PermissionError if the user does not have the permission."""
        if not self.has_permission(user, permission):
            raise PermissionError(f"User lacks permission {permission}")

    def grant_permission(self, user: Any, permission: Any, admin_user: Any = None) -> None:
        """Grant a permission to a user (requires an admin granter)."""
        if not self._is_admin(admin_user):
            raise PermissionError("Only admins can grant permissions")
        user_perms = list(getattr(user, "permissions", []))
        if permission not in user_perms:
            user_perms.append(permission)
            user.permissions = user_perms

    def revoke_permission(self, user: Any, permission: Any) -> None:
        """Revoke a permission from a user (audited, SEC-006)."""
        user_perms = list(getattr(user, "permissions", []))
        if permission in user_perms:
            user_perms.remove(permission)
            user.permissions = user_perms
            self.audit.record(
                "revoke", user=getattr(user, "username", "?"), permission=str(permission)
            )

    def grant_temporary_permission(
        self,
        user: Any,
        permission: Any,
        admin_user: Any = None,
        duration_seconds: int = 60,
    ) -> Any:
        """Grant a REAL temporary permission (SEC-002/003).

        Previously this was a permanent, self-granted write to
        ``user.permissions`` with the duration ignored — a privilege-
        escalation primitive. Now:

        - requires an admin granter (SEC-003: no self-grants)
        - expires after ``duration_seconds``
        - recorded as a ``PermissionGrant`` on ``user.temp_permissions``
        - audited via structured log (SEC-006-lite)
        """
        if not self._is_admin(admin_user):
            raise PermissionError("Only admins can grant temporary permissions")
        grant = PermissionGrant(
            permission=permission,
            granted_at=time.time(),
            expires_at=time.time() + duration_seconds,
            granted_by=str(getattr(admin_user, "username", "admin")),
        )
        grants = list(getattr(user, "temp_permissions", []) or [])
        grants.append(grant)
        user.temp_permissions = grants
        self.audit.record(
            "grant",
            user=getattr(user, "username", "?"),
            permission=str(permission),
            ttl=duration_seconds,
            by=grant.granted_by,
        )
        logger.info(
            "perm_grant user=%s permission=%s ttl=%ss by=%s",
            getattr(user, "username", "?"),
            permission,
            duration_seconds,
            grant.granted_by,
        )
        return grant

    def get_role_permissions(self, role: Any) -> list[Any]:
        """Return the default permissions associated with a role."""
        if role == Role.ADMIN:
            return list(Permission)
        if role == Role.OPERATOR:
            return [
                Permission.READ_ALERTS,
                Permission.READ_CASES,
                Permission.CREATE_CASES,
                Permission.UPDATE_CASES,
            ]
        if role == Role.ANALYST:
            return [
                Permission.READ_ALERTS,
                Permission.READ_CASES,
                Permission.CREATE_CASES,
            ]
        if role in (Role.VIEWER, Role.READONLY):
            return [Permission.READ_ALERTS, Permission.READ_CASES]
        return []

    # AUTH-003: real API-surface role map. Privilege order
    # ADMIN > OPERATOR > ANALYST > VIEWER/READONLY:
    #   viewer   → read-only (GET outside admin paths)
    #   analyst  → + alert submission and IoC caching
    #   operator → + containment actions and queue/DLQ management
    #   admin    → + backups, test runner, audit trail, /api/admin*
    _ADMIN_PREFIXES = (
        "/backup",
        "/tests/run",
        "/api/v1/audit",
        "/api/v1/config",
        "/api/admin",
    )
    _OPERATOR_PREFIXES = ("/api/v1/contain", "/api/v1/queue")
    _ANALYST_POST_PREFIXES = ("/api/v1/alerts", "/api/v1/cache/ioc")

    def can_access_endpoint(self, user: Any, path: str, method: str) -> bool:
        """Return True if the user may access the given endpoint/method."""
        method = method.upper()
        role = getattr(user, "role", None)

        if role == Role.ADMIN:
            return True

        if path.startswith(self._ADMIN_PREFIXES):
            return False

        if path.startswith(("/auth/", "/api/v1/auth/")):
            # Session bootstrap (ws-ticket, verify) — any authenticated role.
            return True

        if path.startswith(self._OPERATOR_PREFIXES):
            return role == Role.OPERATOR

        if method == "GET":
            return role in (
                Role.VIEWER,
                Role.READONLY,
                Role.ANALYST,
                Role.OPERATOR,
            ) or self.has_permission(user, Permission.READ_ALERTS)

        if role in (Role.ANALYST, Role.OPERATOR):
            if path.startswith(self._ANALYST_POST_PREFIXES):
                return True

        if method == "POST" and self.has_permission(user, Permission.CREATE_CASES):
            return True
        return False

    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify username and password against ConfigProvider.

        In production, use a proper authentication system with password
        hashing.
        """
        env_username = self.config_provider.get("web_ui_user") or ""
        env_password = self.config_provider.get("web_ui_password") or ""

        if not env_username or not env_password:
            logger.error("WEB_UI_USER or WEB_UI_PASSWORD not configured")
            return False

        is_valid = hmac.compare_digest(
            username.encode("utf-8"), env_username.encode("utf-8")
        ) and hmac.compare_digest(password.encode("utf-8"), env_password.encode("utf-8"))

        if is_valid:
            logger.info(f"Successful login for user: {username}")
        else:
            logger.warning(f"Failed login attempt for user: {username}")

        return is_valid

    def create_jwt_token(self, username: str) -> str:
        """Create a JWT token for the given username.

        Delegates to TokenProviderInterface for actual token creation.
        """
        secret_key = self._get_auth_secret()
        if not secret_key:
            raise AuthError("Authentication system not properly configured", 500)
        self._validate_secret_length(secret_key)

        expiration_minutes = self.config_provider.get("JWT_EXPIRATION_MINUTES", 60)
        algorithm = self.config_provider.get("JWT_ALGORITHM", JWT_ALGORITHM_DEFAULT)

        role = str(self.config_provider.get("WEB_UI_ROLE", "admin") or "admin")
        return self.token_provider.create_token(
            username,
            secret_key,
            expiration_minutes,
            algorithm,
            extra_claims={"role": role},
        )

    def verify_jwt_token(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return the payload.

        Delegates to TokenProviderInterface for actual token
        verification.
        """
        secret_key = self._get_auth_secret()
        if not secret_key:
            raise AuthError("Authentication system not properly configured", 500)
        self._validate_secret_length(secret_key)

        algorithm = self.config_provider.get("JWT_ALGORITHM", JWT_ALGORITHM_DEFAULT)
        return self.token_provider.verify_token(token, secret_key, algorithm)
