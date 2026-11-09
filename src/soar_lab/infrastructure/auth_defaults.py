"""Default provider factories for AuthService.

This module lives in the infrastructure layer so that the application
layer (``auth_service.py``) does not need to import infrastructure
directly.  The composition root or tests can call these factories to
obtain working default providers.
"""

from typing import Any

from soar_lab.config.logging import get_logger
from soar_lab.config.settings import create_settings
from soar_lab.domain.ports import TokenProviderInterface
from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider

logger = get_logger(__name__)

__all__ = [
    "create_default_config_provider",
    "create_default_config_provider_wrapper",
    "create_default_token_provider_wrapper",
]


def create_default_config_provider() -> "InfrastructureConfigProvider | None":
    """Return a default config provider backed by Settings.

    Returns:
        An InfrastructureConfigProvider, or None if settings cannot be
        loaded (e.g. during test collection without a .env file). The
        failure is logged — a silent ``None`` would let the app boot with
        every config key silently defaulting.
    """
    try:
        return InfrastructureConfigProvider(create_settings())
    except Exception as exc:
        logger.warning("Default config provider unavailable: %s", exc)
        return None


class _SimpleConfigProvider:
    """Minimal config provider used when no explicit provider is supplied.

    When the underlying Settings-backed provider cannot be constructed the
    instance still answers ``get()``/``get_service_urls()`` with caller
    defaults — but the degraded state is logged at construction and exposed
    via :attr:`available` so callers can distinguish "key absent" from
    "config backend broken".
    """

    def __init__(self) -> None:
        self._provider = create_default_config_provider()
        if self._provider is None:
            logger.warning(
                "Config backend unavailable — _SimpleConfigProvider returns "
                "caller-supplied defaults for every key"
            )

    @property
    def available(self) -> bool:
        """Whether a real config backend is serving this provider."""
        return self._provider is not None

    def get(self, key: str, default: Any = None) -> Any:
        if self._provider is not None:
            return self._provider.get(key, default)
        return default

    def get_service_urls(self) -> dict[str, Any]:
        if self._provider is not None:
            return self._provider.get_service_urls()
        return {}


class _SimpleTokenProvider:
    """Minimal token provider used when no explicit provider is supplied."""

    def __init__(self) -> None:
        self._provider: TokenProviderInterface = JWTTokenProvider()

    def create_token(
        self,
        username: str,
        secret: str,
        expiration_minutes: int,
        algorithm: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        return self._provider.create_token(
            username, secret, expiration_minutes, algorithm, extra_claims=extra_claims
        )

    def verify_token(self, token: str, secret: str, algorithm: str) -> dict[str, Any]:
        return self._provider.verify_token(token, secret, algorithm)


def create_default_config_provider_wrapper() -> _SimpleConfigProvider:
    """Return a _SimpleConfigProvider instance."""
    return _SimpleConfigProvider()


def create_default_token_provider_wrapper() -> _SimpleTokenProvider:
    """Return a _SimpleTokenProvider instance."""
    return _SimpleTokenProvider()
