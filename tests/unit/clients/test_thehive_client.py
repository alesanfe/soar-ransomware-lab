#!/usr/bin/env python3
"""Unit tests for soar_lab.integrations.thehive_client."""

from unittest.mock import Mock

import pytest

from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient


class TestTheHiveClient:
    """Test TheHiveClient integration adapter."""

    def test_initialization_with_base_url_and_api_key(self):
        """Test successful initialization with base_url and api_key."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")

        # When running inside Docker, localhost URLs are converted to container names
        import os

        if os.path.exists("/.dockerenv"):
            assert client.base_url == "https://thehive:9443"
        else:
            assert client.base_url == "http://localhost:9000"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider."""
        mock_config_provider = Mock()
        mock_config_provider.get.side_effect = lambda key, default=None: {
            "thehive_url": "http://localhost:9000",
            "thehive_api_key": "test-key",
        }.get(key, default)

        client = TheHiveClient(base_url=None, api_key=None, config_provider=mock_config_provider)

        # When running inside Docker, localhost URLs are converted to container names
        import os

        if os.path.exists("/.dockerenv"):
            assert client.base_url == "https://thehive:9443"
        else:
            assert client.base_url == "http://localhost:9000"

    def test_initialization_requires_url(self):
        """Test that base_url is required when not in config_provider."""
        with pytest.raises(ValueError, match="thehive_url must be provided"):
            TheHiveClient(base_url=None, api_key="test-key")

    def test_initialization_requires_api_key(self):
        """Test that api_key is required when not in config_provider."""
        with pytest.raises(ValueError, match="thehive_api_key must be provided"):
            TheHiveClient(base_url="http://localhost:9000", api_key=None)

    def test_initialization_config_provider_missing_url(self):
        """Test that config_provider must provide thehive_url."""
        mock_config_provider = Mock()
        mock_config_provider.get.return_value = None

        with pytest.raises(ValueError, match="thehive_url must be provided"):
            TheHiveClient(base_url=None, api_key=None, config_provider=mock_config_provider)

    def test_initialization_config_provider_missing_api_key(self):
        """Test that config_provider must provide thehive_api_key."""
        mock_config_provider = Mock()
        mock_config_provider.get.side_effect = lambda key, default=None: {
            "thehive_url": "http://localhost:9000",
            "thehive_api_key": None,
        }.get(key, default)

        with pytest.raises(ValueError, match="thehive_api_key must be provided"):
            TheHiveClient(base_url=None, api_key=None, config_provider=mock_config_provider)

    def test_create_alert(self):
        """Test creating an alert."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "alert-123"})

        alert = {"title": "Test Alert", "type": "external"}
        result = client.create_alert(alert)

        client.post.assert_called_once_with("/api/v1/alert", data=alert)
        assert result == {"id": "alert-123"}

    def test_create_case(self):
        """Test creating a case."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "case-123"})

        case = {"title": "Test Case", "severity": 2}
        result = client.create_case(case)

        client.post.assert_called_once_with("/api/v1/case", data=case)
        assert result == {"id": "case-123"}

    def test_get_case(self):
        """Test retrieving a case by ID."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value={"id": "case-123", "title": "Test Case"})

        result = client.get_case("case-123")

        client.get.assert_called_once_with("/api/v1/case/case-123")
        assert result == {"id": "case-123", "title": "Test Case"}

    def test_add_observable(self):
        """Test adding an observable to a case."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "obs-123"}])

        observable = {"dataType": "ip", "data": "192.168.1.1"}
        result = client.add_observable("case-123", observable)

        # TheHive 5 uses /api/v1/case/{case_id}/observable; a list response
        # is normalized to its first element.
        expected_payload = {
            "dataType": "ip",
            "data": "192.168.1.1",
            "tlp": 2,
            "ioc": True,
            "sighted": False,
            "tags": [],
            "message": "",
        }
        client.post.assert_called_once_with(
            "/api/v1/case/case-123/observable", data=expected_payload
        )
        assert result == {"id": "obs-123"}

    def test_add_observable_multi_status_dict(self):
        """Partial-success dict responses are unwrapped to the first success."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"success": [{"id": "obs-1"}], "failure": []})

        result = client.add_observable("case-123", {"dataType": "ip", "data": "1.2.3.4"})

        assert result == {"id": "obs-1"}

    def test_add_observable_all_failures_raises(self):
        """A response with only failures raises RuntimeError."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"success": [], "failure": [{"message": "bad dataType"}]})

        with pytest.raises(RuntimeError, match="observable creation failed"):
            client.add_observable("case-123", {"dataType": "ip", "data": "1.2.3.4"})

    def test_list_cases(self):
        """Test listing all cases (TheHive 5 query API)."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "case-1"}, {"id": "case-2"}])

        result = client.list_cases()

        client.post.assert_called_once_with(
            "/api/v1/query",
            data={
                "query": [
                    {"_name": "listCase"},
                    {"_name": "sort", "_fields": [{"number": "desc"}]},
                    {"_name": "page", "from": 0, "to": 1000},
                ]
            },
        )
        assert result == [{"id": "case-1"}, {"id": "case-2"}]

    def test_list_cases_empty(self):
        """Test listing cases when response is not a list."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"error": "not found"})

        result = client.list_cases()

        assert result == []

    def test_search_cases(self):
        """Test searching cases with filter (TheHive 5 query API)."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "case-1"}])

        result = client.search_cases(query={"status": "New"}, range_="0-50")

        expected_data = {
            "query": [
                {"_name": "listCase"},
                {"_name": "filter", "status": "New"},
                {"_name": "sort", "_fields": [{"number": "desc"}]},
                {"_name": "page", "from": 0, "to": 50},
            ]
        }
        client.post.assert_called_once_with("/api/v1/query", data=expected_data)
        assert result == [{"id": "case-1"}]

    def test_search_cases_default_params(self):
        """Test searching cases with default parameters (no filter op)."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "case-1"}])

        result = client.search_cases()

        expected_data = {
            "query": [
                {"_name": "listCase"},
                {"_name": "sort", "_fields": [{"number": "desc"}]},
                {"_name": "page", "from": 0, "to": 1000},
            ]
        }
        client.post.assert_called_once_with("/api/v1/query", data=expected_data)
        assert result == [{"id": "case-1"}]

    def test_get_case_observables(self):
        """Test getting case observables (query API traversal)."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "obs-1"}, {"id": "obs-2"}])

        result = client.get_case_observables("case-123")

        client.post.assert_called_once_with(
            "/api/v1/query",
            data={
                "query": [
                    {"_name": "getCase", "idOrName": "case-123"},
                    {"_name": "observables"},
                ]
            },
        )
        assert result == [{"id": "obs-1"}, {"id": "obs-2"}]

    def test_close_case(self):
        """Test closing a case (status is a TH5 Closed-stage value)."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.patch = Mock(return_value={})

        result = client.close_case("case-123", resolution="TruePositive", summary="Test summary")

        client.patch.assert_called_once_with(
            "/api/v1/case/case-123",
            data={"status": "TruePositive", "summary": "Test summary"},
        )
        assert result == {}

    def test_close_case_default_params(self):
        """Test closing a case with default parameters."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.patch = Mock(return_value={})

        result = client.close_case("case-123")

        client.patch.assert_called_once_with(
            "/api/v1/case/case-123",
            data={"status": "TruePositive", "summary": ""},
        )
        assert result == {}

    def test_list_case_tasks(self):
        """Test listing case tasks (query API traversal)."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "task-1"}, {"id": "task-2"}])

        result = client.list_case_tasks("case-123")

        client.post.assert_called_once_with(
            "/api/v1/query",
            data={
                "query": [
                    {"_name": "getCase", "idOrName": "case-123"},
                    {"_name": "tasks"},
                ]
            },
        )
        assert result == [{"id": "task-1"}, {"id": "task-2"}]

    def test_list_case_tasks_empty(self):
        """Test listing case tasks when response is not a list."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"error": "not found"})

        result = client.list_case_tasks("case-123")

        assert result == []

    def test_health_check_success(self):
        """Test health check when service is reachable."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value={"status": "ok"})

        result = client.health_check()

        assert result is True

    def test_health_check_failure(self):
        """Test health check when service is not reachable."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(side_effect=Exception("Connection error"))

        result = client.health_check()

        assert result is False


class TestTheHiveClientBranchCoverage:
    """Cover create_case kwargs path, update/delete, search sort/range
    branches, and the pure migration/compatibility helpers."""

    @pytest.fixture
    def client(self):
        return TheHiveClient(base_url="http://localhost:9000", api_key="test-key")

    def test_create_case_from_kwargs_with_tags_and_template(self, client):
        client.post = Mock(return_value={"id": "c1"})
        result = client.create_case(
            title="T",
            description="D",
            severity=2,
            tlp=1,
            pap=0,
            tags=["x"],
            template="tpl",
            extra="e",
        )
        data = client.post.call_args.kwargs["data"]
        assert data["title"] == "T"
        assert data["tags"] == ["x"]
        assert data["template"] == "tpl"
        assert data["extra"] == "e"  # kwargs merged in
        assert result == {"id": "c1"}

    def test_create_case_from_kwargs_minimal(self, client):
        client.post = Mock(return_value={})
        client.create_case(title="T", description="D", severity=1, tlp=0, pap=0)
        data = client.post.call_args.kwargs["data"]
        assert "tags" not in data
        assert "template" not in data

    def test_update_case_patches(self, client):
        client.patch = Mock(return_value={"id": "c1", "status": "New"})
        result = client.update_case("c1", status="New")
        client.patch.assert_called_once_with("/api/v1/case/c1", data={"status": "New"})
        assert result["status"] == "New"

    def test_delete_case(self, client):
        client.delete = Mock(return_value={"id": "c1"})
        assert client.delete_case("c1") == {"id": "c1"}
        client.delete.assert_called_once_with("/api/v1/case/c1")

    def test_create_observable_delegates_with_defaults(self, client):
        client.post = Mock(return_value={"id": "o1"})
        client.create_observable("c1", "ip", "10.0.0.1", tlp=3)
        data = client.post.call_args.kwargs["data"]
        assert data["dataType"] == "ip"
        assert data["tlp"] == 3
        assert data["ioc"] is True
        assert data["tags"] == []

    def test_list_cases_sort_list_serializes(self, client):
        client.post = Mock(
            return_value=[{"id": "c1", "status": "New"}, {"id": "c2", "status": "Deleted"}]
        )
        result = client.list_cases(sort=["-caseId"])
        ops = client.post.call_args.kwargs["data"]["query"]
        assert ops[1] == {"_name": "sort", "_fields": [{"number": "desc"}]}
        assert result == [{"id": "c1", "status": "New"}]  # Deleted filtered

    def test_list_cases_sort_str_passthrough(self, client):
        client.post = Mock(return_value=[])
        client.list_cases(sort="-createdAt")
        ops = client.post.call_args.kwargs["data"]["query"]
        assert ops[1] == {"_name": "sort", "_fields": [{"_createdAt": "desc"}]}

    def test_search_cases_with_sort_and_range(self, client):
        client.post = Mock(
            return_value=[{"id": "c1", "status": "New"}, {"id": "c2", "status": "Deleted"}]
        )
        result = client.search_cases(query={"q": 1}, range_="0-50", sort=["-caseId"])
        ops = client.post.call_args.kwargs["data"]["query"]
        assert ops[1] == {"_name": "filter", "q": 1}
        assert ops[2] == {"_name": "sort", "_fields": [{"number": "desc"}]}
        assert ops[3] == {"_name": "page", "from": 0, "to": 50}
        assert result == [{"id": "c1", "status": "New"}]

    def test_search_cases_non_list_result_returns_empty(self, client):
        client.post = Mock(return_value={"error": "x"})
        assert client.search_cases(query={"q": 1}) == []

    def test_get_version(self, client):
        client.get = Mock(return_value={"status": "ok"})
        assert client.get_version() == {"status": "ok"}
        client.get.assert_called_once_with("/api/status")


class TestTheHiveClientPureHelpers:
    """Migration/compat helpers — no HTTP."""

    @pytest.fixture
    def client(self):
        return TheHiveClient(base_url="http://localhost:9000", api_key="test-key")

    def test_migrate_case_format_converts_str_severity(self, client):
        out = client.migrate_case_format({"severity": "3", "title": "T"})
        assert out["severity"] == 3
        assert out["tags"] == []

    def test_migrate_case_format_keeps_unparseable_severity(self, client):
        out = client.migrate_case_format({"severity": "high", "tags": ["a"]})
        assert out["severity"] == "high"
        assert out["tags"] == ["a"]

    def test_migrate_case_format_int_severity_untouched(self, client):
        out = client.migrate_case_format({"severity": 2})
        assert out["severity"] == 2

    def test_rollback_data_format(self, client):
        out = client.rollback_data_format({"a": 1, "new_field": 2, "version": "9"})
        assert out == {"a": 1, "version": "4.0.0"}

    def test_check_schema_compatibility(self, client):
        assert client.check_schema_compatibility({"a": 1}, {"a": 1, "b": 2}) is True
        assert client.check_schema_compatibility({"a": 1, "c": 3}, {"a": 1}) is False

    def test_process_deprecated_fields(self, client):
        out = client.process_deprecated_fields({"keep": 1, "old_x": 2, "deprecated_y": 3})
        assert out == {"keep": 1}

    def test_check_version_compatibility(self, client):
        assert client.check_version_compatibility("5.1.0", "5.0.0") is True
        assert client.check_version_compatibility("4.0", "5.0.0") is False
        assert client.check_version_compatibility("5.0", "5.0.0") is True  # pad
        assert client.check_version_compatibility("", "1.0") is False
        assert client.check_version_compatibility("x.y", "1.0") is False
