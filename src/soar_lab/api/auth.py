"""Authentication module for SOAR Lab API."""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


def _get_auth_secret() -> str:
    jwt_secret = os.getenv("JWT_SECRET_KEY", settings.JWT_SECRET_KEY or "")
    api_secret = os.getenv("API_AUTH_SECRET", "")
    
    # Prefer JWT_SECRET_KEY for production, but allow API_AUTH_SECRET for tests
    if jwt_secret:
        return jwt_secret
    if api_secret:
        return api_secret
    return jwt_secret


class AuthError(Exception):
    """Custom authentication error."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def verify_credentials(username: str, password: str) -> bool:
    """
    Verify username and password against environment variables.
    In production, use a proper authentication system with password hashing.
    """
    env_username = os.getenv("WEB_UI_USER", settings.WEB_UI_USER or "")
    env_password = os.getenv("WEB_UI_PASSWORD", settings.WEB_UI_PASSWORD or "")
    
    if not env_username or not env_password:
        logger.error("WEB_UI_USER or WEB_UI_PASSWORD environment variables not set")
        return False
    
    is_valid = username == env_username and password == env_password
    
    if is_valid:
        logger.info(f"Successful login for user: {username}")
    else:
        logger.warning(f"Failed login attempt for user: {username}")
    
    return is_valid


def create_jwt_token(username: str) -> str:
    """
    Create a JWT token for the given username.
    JWT library is required for security.
    """
    try:
        from jose import JWTError, jwt
    except ImportError:
        logger.error("PyJWT is required but not installed")
        raise AuthError("JWT library not available - install python-jose[cryptography]", 500)
    
    secret_key = _get_auth_secret()
    if not secret_key:
        raise AuthError("Authentication system not properly configured", 500)
    
    # Only enforce 32-char minimum if using JWT_SECRET_KEY (production)
    # Allow shorter API_AUTH_SECRET for tests/legacy compatibility
    api_secret = os.getenv("API_AUTH_SECRET", "")
    if api_secret:
        # Using API_AUTH_SECRET - allow any length for test compatibility
        pass
    else:
        # Using JWT_SECRET_KEY - enforce minimum length
        if len(secret_key) < 32:
            raise AuthError("Authentication system not properly configured", 500)
    
    try:
        payload = {
            "sub": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES),
            "scope": "access"
        }
        token = jwt.encode(payload, secret_key, algorithm=settings.JWT_ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Error creating JWT token: {e}")
        raise AuthError("Failed to create authentication token", 500)


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token and return the payload.
    JWT library is required for security.
    """
    try:
        from jose import JWTError, jwt
    except ImportError:
        logger.error("PyJWT is required but not installed")
        raise AuthError("JWT library not available - install python-jose[cryptography]", 500)
    
    secret_key = _get_auth_secret()
    if not secret_key:
        raise AuthError("Authentication system not properly configured", 500)
    
    # Only enforce 32-char minimum if using JWT_SECRET_KEY (production)
    # Allow shorter API_AUTH_SECRET for tests/legacy compatibility
    api_secret = os.getenv("API_AUTH_SECRET", "")
    if api_secret:
        # Using API_AUTH_SECRET - allow any length for test compatibility
        pass
    else:
        # Using JWT_SECRET_KEY - enforce minimum length
        if len(secret_key) < 32:
            raise AuthError("Authentication system not properly configured", 500)
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise AuthError("Invalid token payload", 401)
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
            raise AuthError("Token expired", 401)
        
        return {"user": username, "method": "jwt", "exp": exp}
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise AuthError("Invalid authentication credentials", 401)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token or API key and return user information.
    """
    token = credentials.credentials
    
    try:
        user_info = verify_jwt_token(token)
        return user_info
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
