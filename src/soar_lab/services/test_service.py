"""Test service for SOAR Lab API."""
import asyncio
import json
from typing import Dict, Any, Optional, Protocol

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import CacheInterface, TestRunner, TestResultParserInterface

logger = get_logger(__name__)


class TestService:
    """Service class for test operations with injected dependencies."""

    def __init__(self, runner: TestRunner, parser: TestResultParserInterface):
        self.runner = runner
        if not parser:
            raise ValueError("parser is required for TestService")
        self.parser = parser

    async def run_tests(self, category: str) -> Dict[str, Any]:
        """Run tests using injected runner and parser."""
        try:
            self._validate_test_category(category)
            # Use async version if available, otherwise use sync version
            if hasattr(self.runner, 'run_suite_async'):
                result = await self.runner.run_suite_async(suite=category, coverage=True)
            else:
                result = self.runner.run_suite(suite=category, coverage=True)
            results = self._parse_test_results(result['output'])

            return {
                "category": category,
                **results,
                "output": result['output'],
                "duration": result['duration']
            }

        except OSError as e:
            logger.error(f"OS error running tests: {e}")
            raise Exception(f"Failed to run tests: {str(e)}")
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            raise Exception(f"Failed to run tests: {str(e)}")

    async def get_test_coverage(self, cache: Optional[CacheInterface] = None) -> Dict[str, float]:
        """Get test coverage using injected runner."""
        coverage_data = self.runner.get_coverage()

        try:
            # Cache the result using injected cache dependency
            if cache:
                cache.setex("test_coverage", 300, json.dumps(coverage_data))

            return coverage_data

        except Exception as e:
            logger.error(f"Error getting coverage: {e}")
            return {"unit": 0, "integration": 0, "overall": 0}

    def _validate_test_category(self, category: str) -> None:
        """
        Validate test category to prevent command injection.

        Args:
            category: Test category to validate

        Raises:
            ValueError: If category is invalid
        """
        allowed_categories = ['unit', 'integration', 'e2e', 'all']
        if category not in allowed_categories:
            raise ValueError(f"Invalid test category: {category}")

        # Validate category doesn't contain path traversal
        if '..' in category or '/' in category or '\\' in category:
            raise ValueError(f"Invalid category path: {category}")

    def _parse_test_results(self, output: str) -> dict:
        """
        Parse test results from pytest output.

        Args:
            output: Pytest output string

        Returns:
            Dict with passed, failed, skipped, and coverage
        """
        return self.parser.parse(output)
