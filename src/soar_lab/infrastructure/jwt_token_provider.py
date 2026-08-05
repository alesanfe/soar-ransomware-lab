"""JWT Token Provider - Infrastructure adapter for token operations.

This adapter implements the TokenProviderInterface using python-jose,
encapsulating the technical details of JWT token creation and verification.
"""

from datetime import datetime, timedelta, timezone
from soar_lab.common.exceptions import AuthError
from typing import Dict, Any

from soar_lab.config.logging import get_logger

try:
    from jose import JWTError, jwt
except ImportError:
    logger = get_logger(__name__)
    logger.error("PyJWT is required but not installed")
    raise ImportError("python-jose[cryptography] is required for JWT authentication")

logger = get_logger(__name__)


class JWTTokenProvider:
    """JWT token provider using python-jose library."""

    def create_token(self, username: str, secret: str, expiration_minutes: int, algorithm: str) -> str:
        """
        Create a JWT token for the given username.

        Args:
            username: Username to encode in the token
            secret: Secret key for signing
            expiration_minutes: Token expiration time in minutes
            algorithm: JWT algorithm (e.g., HS256)

        Returns:
            Encoded JWT token string
        """
        try:
            now = datetime.now(timezone.utc)
            payload = {
                "sub": username,
                "iat": now,
                "exp": now + timedelta(minutes=expiration_minutes),
                "scope": "access"
            }
            token = jwt.encode(payload, secret, algorithm=algorithm)
            return token
        except Exception as e:
            logger.error(f"Error creating JWT token: {e}")
            raise AuthError("Failed to create authentication token", 500)

    def verify_token(self, token: str, secret: str, algorithm: str) -> Dict[str, Any]:
        """
        Verify a JWT token and return the payload.

        Args:
            token: JWT token string to verify
            secret: Secret key for verification
            algorithm: JWT algorithm used for signing

        Returns:
            Decoded token payload as dictionary

        Raises:
            AuthError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, secret, algorithms=[algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise AuthError("Invalid token payload", 401)
            return {"user": username, "method": "jwt", "exp": payload.get("exp")}
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise AuthError("Invalid authentication credentials", 401)
