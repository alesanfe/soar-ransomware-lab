"""PytestTestRunner - encapsulates pytest execution knowledge.

This adapter isolates the application layer from subprocess details.
The service layer only knows about TestRunner.run_suite/get_coverage,
not about pytest arguments or asyncio.create_subprocess_exec.
"""

import asyncio
import contextlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from soar_lab.common.constants import DEFAULT_TEST_TIMEOUT
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.subprocess_runner import _kill_process_tree

__all__ = ["PytestTestRunner", "TestRunResult"]

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TestRunResult:
    """Typed result of a pytest suite execution.

    ``returncode`` is always an ``int``: a missing/unknown exit state is
    reported as ``-1``, never coerced to a false ``0`` success.
    """

    returncode: int
    stdout: str
    stderr: str
    duration: float

    @property
    def success(self) -> bool:
        """True only when the suite exited with code 0."""
        return self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        """Return the dict shape required by the TestRunner port."""
        return asdict(self)


class PytestTestRunner:
    """Adapter that encapsulates pytest test execution."""

    def __init__(
        self,
        repo_root: Path,
        path_service: object,
        timeout: int = DEFAULT_TEST_TIMEOUT,
    ) -> None:
        if not repo_root:
            raise ValueError("repo_root is required for PytestTestRunner")
        if not path_service:
            raise ValueError("path_service is required for PytestTestRunner")
        self._repo_root = repo_root
        self._path_service = path_service
        self._timeout = timeout

    # Categories that map to a dedicated tests/ subdirectory
    _FOLDER_CATEGORIES = {"unit", "integration", "e2e", "atomic", "performance", "security"}

    def _build_pytest_cmd(self, suite: str, coverage: bool) -> list:
        """Build the pytest command for a given suite name."""
        base_cmd = ["python", "-m", "pytest"]

        if suite == "all":
            base_cmd.extend(["tests/", "-v", "--tb=short"])
        elif suite == "smoke":
            # smoke uses the pytest marker, not a separate folder
            base_cmd.extend(["tests/", "-m", "smoke", "-v", "--tb=short"])
        elif suite in self._FOLDER_CATEGORIES:
            base_cmd.extend([f"tests/{suite}", "-v", "--tb=short"])
        else:
            raise ValueError(f"Unknown test suite: {suite}")

        if coverage:
            base_cmd.extend(["--cov=src/soar_lab", "--cov-report=json"])

        return base_cmd

    @staticmethod
    def _to_port_dict(result: TestRunResult) -> dict[str, Any]:
        """Map a typed result to the dict shape the TestRunner port declares."""
        return {
            "status": "success" if result.success else "error",
            "output": result.stdout,
            "error": result.stderr,
            "duration": result.duration,
            "returncode": result.returncode,
        }

    def run_suite(self, suite: str, coverage: bool = True) -> dict[str, Any]:
        """Run a test suite and return results (synchronous wrapper)."""
        result = asyncio.run(self._run_async(self._build_pytest_cmd(suite, coverage)))
        return self._to_port_dict(result)

    async def run_suite_async(self, suite: str, coverage: bool = True) -> dict[str, Any]:
        """Run a test suite and return results (async version for FastAPI)."""
        result = await self._run_async(self._build_pytest_cmd(suite, coverage))
        return self._to_port_dict(result)

    def get_coverage(self) -> dict[str, float | None | bool]:
        """Get current test coverage from coverage.json.

        Absence of measurement data is reported explicitly
        (``measured=False``, values ``None``) — never as a fake 0% that a
        dashboard cannot distinguish from a real zero. Per-suite coverage
        beyond the aggregate is not currently measured, so ``integration``
        is ``None`` rather than a hardcoded ``0``.
        """
        coverage_file = self._path_service.coverage_file

        if not coverage_file.exists():
            return {
                "unit": None,
                "integration": None,
                "overall": None,
                "measured": False,
            }

        with open(coverage_file, encoding="utf-8") as f:
            coverage_data = json.load(f)

        percent = coverage_data.get("totals", {}).get("percent_covered")
        return {
            "unit": percent,
            "integration": None,
            "overall": percent,
            "measured": percent is not None,
        }

    async def _run_async(self, cmd: list) -> TestRunResult:
        """Run command asynchronously, killing the whole process tree on timeout."""
        t0 = time.monotonic()

        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self._repo_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
            duration = time.monotonic() - t0

            return TestRunResult(
                # ``None`` (process state unknown) must never coerce to a
                # success code — a missing returncode is reported as -1.
                returncode=proc.returncode if proc.returncode is not None else -1,
                stdout=stdout_b.decode("utf-8", errors="ignore"),
                stderr=stderr_b.decode("utf-8", errors="ignore"),
                duration=duration,
            )
        except TimeoutError:
            logger.warning(f"Test suite timed out after {self._timeout}s")
            if proc is not None and proc.returncode is None:
                _kill_process_tree(proc.pid)
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(proc.wait(), timeout=5)
            return TestRunResult(
                returncode=-1,
                stdout="",
                stderr=f"Timeout after {self._timeout}s",
                duration=time.monotonic() - t0,
            )
