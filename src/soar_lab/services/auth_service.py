"""Authentication Service for SOAR Lab.

This service contains authentication logic as a use case,
separated from the FastAPI adapter layer.
"""

from typing import Dict, Any

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import TokenProviderInterface
from soar_lab.exceptions import AuthError

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations with injected dependencies."""

    def __init__(self, config_provider: object, token_provider: TokenProviderInterface):
        """
        Initialize the authentication service.

        Args:
            config_provider: Configuration provider for auth settings (required)
            token_provider: Token provider for JWT operations (required)
        """
        if not config_provider:
            raise ValueError("config_provider is required for AuthService")
        if not token_provider:
            raise ValueError("token_provider is required for AuthService")
        self.config_provider = config_provider
        self.token_provider = token_provider

    def _get_auth_secret(self) -> str:
        """Get authentication secret from ConfigProvider."""
        return self.config_provider.get('jwt_secret_key') or self.config_provider.get('api_auth_secret') or ""

    def _validate_secret_length(self, secret: str) -> None:
        """Enforce minimum key length when not using a legacy API_AUTH_SECRET."""
        api_secret = self.config_provider.get('api_auth_secret') or ""
        if not api_secret and len(secret) < 32:
            raise AuthError("Authentication system not properly configured", 500)

    def verify_credentials(self, username: str, password: str) -> bool:
        """
        Verify username and password against ConfigProvider.
        In production, use a proper authentication system with password hashing.
        """
        env_username = self.config_provider.get('web_ui_user') or ""
        env_password = self.config_provider.get('web_ui_password') or ""

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
        """
        Create a JWT token for the given username.
        Delegates to TokenProviderInterface for actual token creation.
        """
        secret_key = self._get_auth_secret()
        if not secret_key:
            raise AuthError("Authentication system not properly configured", 500)
        self._validate_secret_length(secret_key)

        expiration_minutes = self.config_provider.get('JWT_EXPIRATION_MINUTES', 60)
        algorithm = self.config_provider.get('JWT_ALGORITHM', 'HS256')

        return self.token_provider.create_token(username, secret_key, expiration_minutes, algorithm)

    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a JWT token and return the payload.
        Delegates to TokenProviderInterface for actual token verification.
        """
        secret_key = self._get_auth_secret()
        if not secret_key:
            raise AuthError("Authentication system not properly configured", 500)
        self._validate_secret_length(secret_key)

        algorithm = self.config_provider.get('JWT_ALGORITHM', 'HS256')
        return self.token_provider.verify_token(token, secret_key, algorithm)
