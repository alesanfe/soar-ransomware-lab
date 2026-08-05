from typing import Any, Dict, List, Optional, Tuple


class ServiceContract:
    def __init__(
        self,
        name: str = "",
        service_name: str = "",
        version: str = "",
        endpoints: Optional[Dict[str, Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
        supported_versions: Optional[List[str]] = None,
        deprecated_versions: Optional[List[str]] = None,
        deprecated_endpoints: Optional[Dict[str, str]] = None,
        required_headers: Optional[List[str]] = None,
        rate_limit: Optional[Dict[str, int]] = None,
        error_schema: Optional[Dict[str, Any]] = None,
        migration_guides: Optional[Dict[str, str]] = None,
    ) -> None:
        self.name = name or service_name
        self.service_name = service_name or name
        self.version = version
        self.endpoints = endpoints or {}
        self.schema = schema or {}
        self.supported_versions = supported_versions or [version] if version else ["1.0.0"]
        self.deprecated_versions = deprecated_versions or []
        self.deprecated_endpoints = deprecated_endpoints or {}
        self.required_headers = required_headers or ["Content-Type"]
        self.rate_limit = rate_limit or {
            "requests_per_minute": 100,
            "requests_per_hour": 5000,
            "requests_per_day": 50000,
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
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceContract":
        """Create a ServiceContract from a dictionary."""
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
        """Return True if the given version is deprecated."""
        return version in self.deprecated_versions

    def get_deprecated_versions(self) -> List[str]:
        """Return list of deprecated versions."""
        return list(self.deprecated_versions)

    def is_endpoint_deprecated(self, endpoint: str) -> bool:
        """Return True if the endpoint is deprecated."""
        return endpoint in self.deprecated_endpoints

    def get_deprecation_warning(self, endpoint: str) -> str:
        """Return deprecation warning message for an endpoint."""
        return self.deprecated_endpoints.get(endpoint, "")

    def get_required_headers(self) -> List[str]:
        """Return required response headers."""
        return list(self.required_headers)

    def get_rate_limit(self) -> Dict[str, int]:
        """Return rate limit configuration."""
        return dict(self.rate_limit)

    def get_error_schema(self) -> Dict[str, Any]:
        """Return schema for error responses."""
        return dict(self.error_schema)

    def get_migration_guide(self, old_version: str, new_version: str) -> str:
        """Return migration guide between two versions."""
        key = f"{old_version}->{new_version}"
        return self.migration_guides.get(key, f"Migrate from {old_version} to {new_version}")


class APIContract:
    def __init__(self, version: str = "", services=None) -> None:
        self.version = version
        self.services = services or []
