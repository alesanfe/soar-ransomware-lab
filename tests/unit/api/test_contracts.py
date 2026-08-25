"""Unit tests for interfaces.api.contracts ServiceContract and APIContract."""

from __future__ import annotations

from soar_lab.interfaces.api.contracts import (
    DEFAULT_RATE_LIMIT_PER_DAY,
    DEFAULT_RATE_LIMIT_PER_HOUR,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    APIContract,
    ServiceContract,
)


class TestServiceContract:
    """Tests for ServiceContract."""

    def test_default_values(self):
        sc = ServiceContract(name="test", version="1.0.0")
        assert sc.name == "test"
        assert sc.service_name == "test"
        assert sc.version == "1.0.0"
        assert sc.endpoints == {}
        assert sc.schema == {}
        assert sc.supported_versions == ["1.0.0"]
        assert sc.deprecated_versions == []
        assert sc.deprecated_endpoints == {}
        assert sc.required_headers == ["Content-Type"]
        assert sc.rate_limit == {
            "requests_per_minute": DEFAULT_RATE_LIMIT_PER_MINUTE,
            "requests_per_hour": DEFAULT_RATE_LIMIT_PER_HOUR,
            "requests_per_day": DEFAULT_RATE_LIMIT_PER_DAY,
        }

    def test_service_name_fallback(self):
        sc = ServiceContract(service_name="my_service")
        assert sc.name == "my_service"
        assert sc.service_name == "my_service"

    def test_custom_values(self):
        sc = ServiceContract(
            name="api",
            version="2.0.0",
            endpoints={"/health": {"method": "GET"}},
            supported_versions=["1.0.0", "2.0.0"],
            deprecated_versions=["1.0.0"],
            deprecated_endpoints={"/old": "Use /new"},
            required_headers=["X-API-Key"],
            rate_limit={"requests_per_minute": 50},
        )
        assert sc.name == "api"
        assert sc.version == "2.0.0"
        assert sc.endpoints == {"/health": {"method": "GET"}}
        assert sc.supported_versions == ["1.0.0", "2.0.0"]
        assert sc.deprecated_versions == ["1.0.0"]
        assert sc.deprecated_endpoints == {"/old": "Use /new"}
        assert sc.required_headers == ["X-API-Key"]
        assert sc.rate_limit == {"requests_per_minute": 50}

    def test_from_dict(self):
        data = {
            "name": "test_service",
            "version": "3.0.0",
            "endpoints": {"/items": {"method": "GET"}},
            "supported_versions": ["2.0.0", "3.0.0"],
            "deprecated_versions": ["2.0.0"],
        }
        sc = ServiceContract.from_dict(data)
        assert sc.name == "test_service"
        assert sc.version == "3.0.0"
        assert sc.endpoints == {"/items": {"method": "GET"}}
        assert sc.supported_versions == ["2.0.0", "3.0.0"]
        assert sc.deprecated_versions == ["2.0.0"]

    def test_from_dict_empty(self):
        sc = ServiceContract.from_dict({})
        assert sc.name == ""
        assert sc.version == ""
        assert sc.supported_versions == ["1.0.0"]

    def test_is_deprecated(self):
        sc = ServiceContract(deprecated_versions=["1.0.0", "2.0.0"])
        assert sc.is_deprecated("1.0.0") is True
        assert sc.is_deprecated("2.0.0") is True
        assert sc.is_deprecated("3.0.0") is False

    def test_get_deprecated_versions(self):
        sc = ServiceContract(deprecated_versions=["1.0.0"])
        result = sc.get_deprecated_versions()
        assert result == ["1.0.0"]
        # Verify it's a copy
        result.append("2.0.0")
        assert sc.deprecated_versions == ["1.0.0"]

    def test_is_endpoint_deprecated(self):
        sc = ServiceContract(deprecated_endpoints={"/old": "Use /new"})
        assert sc.is_endpoint_deprecated("/old") is True
        assert sc.is_endpoint_deprecated("/new") is False

    def test_get_deprecation_warning(self):
        sc = ServiceContract(deprecated_endpoints={"/old": "Use /new instead"})
        assert sc.get_deprecation_warning("/old") == "Use /new instead"
        assert sc.get_deprecation_warning("/new") == ""

    def test_get_required_headers(self):
        sc = ServiceContract(required_headers=["X-API-Key", "Content-Type"])
        result = sc.get_required_headers()
        assert result == ["X-API-Key", "Content-Type"]
        # Verify it's a copy
        result.append("X-Extra")
        assert sc.required_headers == ["X-API-Key", "Content-Type"]

    def test_get_rate_limit(self):
        sc = ServiceContract(rate_limit={"requests_per_minute": 200})
        result = sc.get_rate_limit()
        assert result == {"requests_per_minute": 200}
        # Verify it's a copy
        result["extra"] = 999
        assert "extra" not in sc.rate_limit

    def test_get_error_schema(self):
        sc = ServiceContract()
        result = sc.get_error_schema()
        assert "type" in result
        assert result["type"] == "object"
        # Verify it's a copy
        result["extra"] = "bad"
        assert "extra" not in sc.error_schema

    def test_get_migration_guide_existing(self):
        sc = ServiceContract(migration_guides={"1.0.0->2.0.0": "Update endpoints"})
        assert sc.get_migration_guide("1.0.0", "2.0.0") == "Update endpoints"

    def test_get_migration_guide_missing(self):
        sc = ServiceContract()
        result = sc.get_migration_guide("1.0.0", "2.0.0")
        assert "Migrate from 1.0.0 to 2.0.0" in result


class TestAPIContract:
    """Tests for APIContract."""

    def test_default_values(self):
        ac = APIContract()
        assert ac.version == ""
        assert ac.services == []

    def test_with_services(self):
        sc1 = ServiceContract(name="svc1")
        sc2 = ServiceContract(name="svc2")
        ac = APIContract(version="1.0.0", services=[sc1, sc2])
        assert ac.version == "1.0.0"
        assert len(ac.services) == 2
        assert ac.services[0].name == "svc1"
        assert ac.services[1].name == "svc2"
