"""API contracts: rate limits, request/response models, and validation."""

# pylint: disable=too-many-instance-attributes
from typing import Any

from soar_lab.common.constants import (
    DEFAULT_API_VERSION,
    DEFAULT_RATE_LIMIT_PER_DAY,
    DEFAULT_RATE_LIMIT_PER_HOUR,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    HEADER_CONTENT_TYPE,
)

__all__ = [
    "DEFAULT_RATE_LIMIT_PER_MINUTE",
    "DEFAULT_RATE_LIMIT_PER_HOUR",
    "DEFAULT_RATE_LIMIT_PER_DAY",
    "ServiceContract",
    "APIContract",
]


class ServiceContract:
    """Describes the contract for a single integration service."""

    def __init__(
        self,
        name: str = "",
        service_name: str = "",
        version: str = "",
        endpoints: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
        supported_versions: list[str] | None = None,
        deprecated_versions: list[str] | None = None,
        deprecated_endpoints: dict[str, str] | None = None,
        required_headers: list[str] | None = None,
        rate_limit: dict[str, int] | None = None,
        error_schema: dict[str, Any] | None = None,
        migration_guides: dict[str, str] | None = None,
    ) -> None:
        self.name = name or service_name
        self.service_name = service_name or name
        self.version = version
        self.endpoints = endpoints or {}
        self.schema = schema or {}
        self.supported_versions = (
            supported_versions or [version] if version else [DEFAULT_API_VERSION]
        )
        self.deprecated_versions = deprecated_versions or []
        self.deprecated_endpoints = deprecated_endpoints or {}
        self.required_headers = required_headers or [HEADER_CONTENT_TYPE]
        self.rate_limit = rate_limit or {
            "requests_per_minute": DEFAULT_RATE_LIMIT_PER_MINUTE,
            "requests_per_hour": DEFAULT_RATE_LIMIT_PER_HOUR,
            "requests_per_day": DEFAULT_RATE_LIMIT_PER_DAY,
        }
        self.error_schema = error_schema or {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "code": {"type": ["integer", "string"]},
                "message": {"type": "string"},
            },
        }
        self.migration_guides = migration_guides or {}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceContract":
        """Create a ServiceContract from a dictionary.

        Args:
            data: Dictionary containing contract fields such as ``name``,
                ``service_name``, ``version``, ``endpoints``, ``schema``,
                ``supported_versions``, ``deprecated_versions``,
                ``deprecated_endpoints``, ``required_headers``,
                ``rate_limit``, ``error_schema``, and ``migration_guides``.

        Returns:
            ServiceContract: A new instance populated from the provided
                dictionary.
        """
        return cls(
            name=data.get("name", ""),
            service_name=data.get("service_name", ""),
            version=data.get("version", ""),
            endpoints=data.get("endpoints", data.get("schema", {})),
            schema=data.get("schema", data.get("endpoints", {})),
            supported_versions=data.get("supported_versions"),
            deprecated_versions=data.get("deprecated_versions"),
            deprecated_endpoints=data.get("deprecated_endpoints"),
            required_headers=data.get("required_headers"),
            rate_limit=data.get("rate_limit"),
            error_schema=data.get("error_schema"),
            migration_guides=data.get("migration_guides"),
        )

    def is_deprecated(self, version: str) -> bool:
        """Return True if the given version is deprecated.

        Args:
            version: The version string to check against the list of
                deprecated versions.

        Returns:
            bool: ``True`` if the version is deprecated, ``False`` otherwise.
        """
        return version in self.deprecated_versions

    def get_deprecated_versions(self) -> list[str]:
        """Return list of deprecated versions.

        Returns:
            list[str]: Copy of the deprecated versions list.
        """
        return self.deprecated_versions.copy()

    def is_endpoint_deprecated(self, endpoint: str) -> bool:
        """Return True if the endpoint is deprecated.

        Args:
            endpoint: The endpoint path to check against the deprecated
                endpoints mapping.

        Returns:
            bool: ``True`` if the endpoint is deprecated, ``False`` otherwise.
        """
        return endpoint in self.deprecated_endpoints

    def get_deprecation_warning(self, endpoint: str) -> str:
        """Return deprecation warning message for an endpoint.

        Args:
            endpoint: The endpoint path to look up in the deprecated
                endpoints mapping.

        Returns:
            str: The deprecation warning message, or an empty string if the
                endpoint has no associated warning.
        """
        return self.deprecated_endpoints.get(endpoint, "")

    def get_required_headers(self) -> list[str]:
        """Return required response headers.

        Returns:
            list[str]: Copy of the required headers list.
        """
        return self.required_headers.copy()

    def get_rate_limit(self) -> dict[str, int]:
        """Return rate limit configuration.

        Returns:
            dict: Copy of the rate limit config (``requests``, ``window``).
        """
        return self.rate_limit.copy()

    def get_error_schema(self) -> dict[str, Any]:
        """Return schema for error responses.

        Returns:
            dict: Copy of the error schema definition.
        """
        return self.error_schema.copy()

    def get_migration_guide(self, old_version: str, new_version: str) -> str:
        """Return migration guide between two versions.

        Args:
            old_version: The version being migrated from.
            new_version: The version being migrated to.

        Returns:
            str: The migration guide for transitioning from
                ``old_version`` to ``new_version``, or a default message if
                no specific guide is registered.
        """
        key = f"{old_version}->{new_version}"
        return self.migration_guides.get(key, f"Migrate from {old_version} to {new_version}")


class APIContract:
    """Top-level container describing the full API contract surface."""

    def __init__(self, version: str = "", services: list[ServiceContract] | None = None) -> None:
        self.version = version
        self.services = services or []
