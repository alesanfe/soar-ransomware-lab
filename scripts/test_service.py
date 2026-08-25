#!/usr/bin/env python3
"""TestService — application use case for running pytest suites.

This module lives in ``scripts/`` for historical reasons but is imported
by the API composition root as a regular module (the repo root is on
``sys.path`` via ``pyproject.toml``). It wraps the test runner + parser
ports into a single service exposed through the ``/tests`` API routes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_CATEGORIES = (
    "unit",
    "integration",
    "e2e",
    "atomic",
    "performance",
    "security",
    "smoke",
    "all",
)


class TestService:
    """Application service that orchestrates test execution and parsing."""

    def __init__(self, runner: Any, parser: Any) -> None:
        if runner is None:
            raise ValueError("runner is required")
        if parser is None:
            raise ValueError("parser is required")
        self.runner = runner
        self.parser = parser

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _validate_test_category(self, category: str) -> None:
        """Validate the test category to prevent path traversal or invalid
        input."""
        if not category or category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid test category: {category!r}")

    def _parse_test_results(self, output: str) -> dict[str, Any]:
        """Parse raw pytest output into a structured result dict."""
        return self.parser.parse(output)

    # ------------------------------------------------------------------
    # Async API
    # ------------------------------------------------------------------
    async def run_tests(self, category: str = "unit", coverage: bool = True) -> dict[str, Any]:
        """Run a test suite by category and return parsed results.

        Supports both async runners (with ``run_suite_async``) and sync
        runners (with ``run_suite``).
        """
        try:
            self._validate_test_category(category)
            if hasattr(self.runner, "run_suite_async"):
                raw = await self.runner.run_suite_async(suite=category, coverage=coverage)
            else:
                raw = self.runner.run_suite(suite=category, coverage=coverage)
        except OSError as exc:
            raise RuntimeError(f"Failed to run tests: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"Failed to run tests: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Failed to run tests: {exc}") from exc

        parsed = self._parse_test_results(raw.get("output", ""))
        return {
            "category": category,
            "passed": parsed.get("passed", 0),
            "failed": parsed.get("failed", 0),
            "output": raw.get("output", ""),
            "duration": raw.get("duration", 0.0),
        }

    async def get_test_coverage(self, cache: Any | None = None) -> dict[str, Any]:
        """Return test coverage per category, optionally caching in Redis."""
        try:
            coverage = self.runner.get_coverage()
        except Exception as exc:
            logger.warning("Failed to get test coverage, using defaults: %s", exc)
            coverage = {"unit": 0, "integration": 0, "overall": 0}

        if cache is not None:
            try:
                cache.setex("test_coverage", 300, json.dumps(coverage))
            except Exception as exc:
                # Cache error — return defaults instead of crashing
                logger.warning("Cache error, returning defaults: %s", exc)
                return {"unit": 0, "integration": 0, "overall": 0}

        return coverage
