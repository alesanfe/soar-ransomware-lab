"""Infrastructure ConfigProvider implementation.

This adapter implements the ConfigProvider port from the domain layer,
wrapping the existing Settings class to provide configuration through
dependency injection instead of global access.
"""

from typing import Any

from soar_lab.config.settings import Settings


class InfrastructureConfigProvider:
    """Infrastructure implementation of ConfigProvider port.

    This class wraps the existing Settings class to provide
    configuration through dependency injection, allowing the application
    layer to be independent of the global settings singleton.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the config provider.

        Args:
            settings: Settings instance (required).
        """
        if not settings:
            raise ValueError("settings is required for InfrastructureConfigProvider")
        self._settings = settings

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.

        Settings already loads all environment variables at initialization,
        so this method only delegates to Settings.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Try to get from Settings object attribute (single source of truth)
        if hasattr(self._settings, key):
            return getattr(self._settings, key)

        # Fall back to Settings._config dict for lowercase keys (e.g. 'web_ui_user')
        cfg = getattr(self._settings, "_config", None)
        if isinstance(cfg, dict) and key in cfg:
            return self._settings._config[key]

        return default

    def get_service_urls(self) -> dict[str, Any]:
        """Get service URLs configuration.

        Returns:
            Dict mapping service names to their health check URLs and container names
        """
        if hasattr(self._settings, "get_service_urls"):
            return self._settings.get_service_urls()
        return {}
