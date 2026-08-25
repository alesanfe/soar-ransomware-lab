"""Authentication Service for SOAR Lab.

This service contains authentication and authorization logic as a use
case, separated from the FastAPI adapter layer.
"""

from collections.abc import Callable
from typing import Any

from soar_lab.common.constants import JWT_ALGORITHM_DEFAULT
from soar_lab.common.exceptions import AuthError
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import TokenProviderInterface

logger = get_logger(__name__)

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
        config_provider: object | None = ...,
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

    def _get_auth_secret(self) -> str:
        """Get authentication secret from ConfigProvider."""
        return (
            self.config_provider.get("jwt_secret_key")
            or self.config_provider.get("api_auth_secret")
            or ""
        )

    def _validate_secret_length(self, secret: str) -> None:
        """Enforce minimum key length when not using a legacy.

        API_AUTH_SECRET.
        """
        api_secret = self.config_provider.get("api_auth_secret") or ""
        if not api_secret and len(secret) < 32:
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
        from soar_lab.auth.models import Role

        return getattr(user, "role", None) == Role.ADMIN

    def has_permission(self, user: Any, permission: Any) -> bool:
        """Return True if the user has the requested permission."""
        from soar_lab.auth.models import Permission

        if self._is_admin(user):
            return True
        user_perms = set(getattr(user, "permissions", []))
        return Permission.ALL in user_perms or permission in user_perms

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
        """Revoke a permission from a user."""
        user_perms = list(getattr(user, "permissions", []))
        if permission in user_perms:
            user_perms.remove(permission)
            user.permissions = user_perms

    def grant_temporary_permission(
        self, user: Any, permission: Any, _duration_seconds: int = 60
    ) -> None:
        """Grant a temporary permission to a user (self-granted, no admin.

        required).
        """
        user_perms = list(getattr(user, "permissions", []))
        if permission not in user_perms:
            user_perms.append(permission)
            user.permissions = user_perms

    def get_role_permissions(self, role: Any) -> list[Any]:
        """Return the default permissions associated with a role."""
        from soar_lab.auth.models import Permission, Role

        if role == Role.ADMIN:
            return list(Permission)
        if role == Role.ANALYST:
            return [
                Permission.READ_ALERTS,
                Permission.READ_CASES,
                Permission.CREATE_CASES,
            ]
        if role == Role.READONLY:
            return [Permission.READ_ALERTS, Permission.READ_CASES]
        return []

    def can_access_endpoint(self, user: Any, path: str, method: str) -> bool:
        """Return True if the user may access the given endpoint/method."""
        from soar_lab.auth.models import Permission, Role

        method = method.upper()
        role = getattr(user, "role", None)

        if role == Role.ADMIN:
            return True

        is_admin_path = path.startswith("/api/admin")
        if is_admin_path:
            return False

        if role == Role.READONLY:
            return method == "GET"

        if role == Role.ANALYST:
            if method == "GET":
                return True
            if method == "POST" and (
                path.startswith("/api/cases") or path.startswith("/api/alerts")
            ):
                return True
            return False

        # Fallback: check explicit permissions
        if method == "GET" and self.has_permission(user, Permission.READ_ALERTS):
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

        is_valid = username == env_username and password == env_password

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

        return self.token_provider.create_token(username, secret_key, expiration_minutes, algorithm)

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
