#!/usr/bin/env python3
"""Unit tests for test_service.py."""

from unittest.mock import AsyncMock, Mock

import pytest

from scripts.test_service import TestService


class TestTestService:
    """Test TestService with mocked dependencies."""

    def test_initialization_success(self):
        """Test successful initialization."""
        mock_runner = Mock()
        mock_parser = Mock()

        service = TestService(runner=mock_runner, parser=mock_parser)

        assert service.runner == mock_runner
        assert service.parser == mock_parser

    def test_requires_parser(self):
        """Test that parser is required."""
        with pytest.raises(ValueError, match="parser is required"):
            TestService(runner=Mock(), parser=None)

    def test_validate_test_category_valid(self):
        """Test validation of valid test category."""
        mock_runner = Mock()
        mock_parser = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        # Should not raise for valid categories
        for cat in (
            "unit",
            "integration",
            "e2e",
            "atomic",
            "performance",
            "security",
            "smoke",
            "all",
        ):
            service._validate_test_category(cat)

    def test_validate_test_category_invalid(self):
        """Test validation of invalid test category."""
        mock_runner = Mock()
        mock_parser = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        with pytest.raises(ValueError, match="Invalid test category"):
            service._validate_test_category("invalid")

    def test_validate_test_category_path_traversal(self):
        """Test validation prevents path traversal."""
        mock_runner = Mock()
        mock_parser = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        # Path traversal is caught by the category validation first
        with pytest.raises(ValueError, match="Invalid test category"):
            service._validate_test_category("../etc")

        with pytest.raises(ValueError, match="Invalid test category"):
            service._validate_test_category("unit/../../etc")

    def test_parse_test_results(self):
        """Test parsing test results."""
        mock_runner = Mock()
        mock_parser = Mock()
        mock_parser.parse.return_value = {"passed": 10, "failed": 0}
        service = TestService(runner=mock_runner, parser=mock_parser)

        result = service._parse_test_results("test output")

        assert result == {"passed": 10, "failed": 0}
        mock_parser.parse.assert_called_once_with("test output")

    @pytest.mark.asyncio
    async def test_run_tests_success(self):
        """Test successful test run."""
        mock_runner = Mock()
        mock_runner.run_suite_async = AsyncMock(
            return_value={"output": "test output", "duration": 5.0}
        )
        mock_parser = Mock()
        mock_parser.parse.return_value = {"passed": 10, "failed": 0}
        service = TestService(runner=mock_runner, parser=mock_parser)

        result = await service.run_tests("unit")

        assert result["category"] == "unit"
        assert result["passed"] == 10
        assert result["failed"] == 0
        assert result["output"] == "test output"
        assert result["duration"] == 5.0

    @pytest.mark.asyncio
    async def test_run_tests_invalid_category(self):
        """Test test run with invalid category."""
        mock_runner = Mock()
        mock_parser = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        with pytest.raises(Exception, match="Failed to run tests"):
            await service.run_tests("invalid")

    @pytest.mark.asyncio
    async def test_get_test_coverage_without_cache(self):
        """Test getting coverage without cache."""
        mock_runner = Mock()
        mock_runner.get_coverage.return_value = {"unit": 80, "integration": 70, "overall": 75}
        mock_parser = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        result = await service.get_test_coverage()

        assert result == {"unit": 80, "integration": 70, "overall": 75}
        mock_runner.get_coverage.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_test_coverage_with_cache(self):
        """Test getting coverage with cache."""
        mock_runner = Mock()
        mock_runner.get_coverage.return_value = {"unit": 80, "integration": 70, "overall": 75}
        mock_parser = Mock()
        mock_cache = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        result = await service.get_test_coverage(cache=mock_cache)

        assert result == {"unit": 80, "integration": 70, "overall": 75}
        mock_cache.setex.assert_called_once_with(
            "test_coverage", 300, '{"unit": 80, "integration": 70, "overall": 75}'
        )

    @pytest.mark.asyncio
    async def test_get_test_coverage_cache_error(self):
        """Test getting coverage with cache error - cache error is caught and returns defaults"""
        mock_runner = Mock()
        mock_runner.get_coverage.return_value = {"unit": 80, "integration": 70, "overall": 75}
        mock_parser = Mock()
        mock_cache = Mock()
        mock_cache.setex.side_effect = Exception("Cache error")
        service = TestService(runner=mock_runner, parser=mock_parser)

        result = await service.get_test_coverage(cache=mock_cache)

        # Cache error is caught by the exception handler, returns defaults
        assert result == {"unit": 0, "integration": 0, "overall": 0}

    @pytest.mark.asyncio
    async def test_run_tests_sync(self):
        """Test test run with sync runner (no run_suite_async)"""
        mock_runner = Mock(spec=["run_suite"])  # Only has run_suite, not run_suite_async
        mock_runner.run_suite.return_value = {"output": "test output", "duration": 5.0}
        mock_parser = Mock()
        mock_parser.parse.return_value = {"passed": 10, "failed": 0}
        service = TestService(runner=mock_runner, parser=mock_parser)

        result = await service.run_tests("unit")

        assert result["category"] == "unit"
        assert result["passed"] == 10
        assert result["failed"] == 0
        mock_runner.run_suite.assert_called_once_with(suite="unit", coverage=True)

    @pytest.mark.asyncio
    async def test_run_tests_os_error(self):
        """Test test run with OSError."""
        mock_runner = Mock()
        mock_runner.run_suite_async = AsyncMock(side_effect=OSError("OS error"))
        mock_parser = Mock()
        service = TestService(runner=mock_runner, parser=mock_parser)

        with pytest.raises(Exception, match="Failed to run tests"):
            await service.run_tests("unit")
