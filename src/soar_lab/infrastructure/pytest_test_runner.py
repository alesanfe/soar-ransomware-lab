"""PytestTestRunner - encapsulates pytest execution knowledge.

This adapter isolates the application layer from subprocess details.
The service layer only knows about TestRunner.run_suite/get_coverage,
not about pytest arguments or asyncio.create_subprocess_exec.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class PytestTestRunner:
    """Adapter that encapsulates pytest test execution."""

    def __init__(self, repo_root: Path, path_service: object, timeout: int = 300):
        if not repo_root:
            raise ValueError("repo_root is required for PytestTestRunner")
        if not path_service:
            raise ValueError("path_service is required for PytestTestRunner")
        self._repo_root = repo_root
        self._path_service = path_service
        self._timeout = timeout

    def run_suite(self, suite: str, coverage: bool = True) -> Dict[str, Any]:
        """Run a test suite and return results (synchronous wrapper)."""
        base_cmd = ['python', '-m', 'pytest']

        if suite == "all":
            base_cmd.extend(['tests/', '-v', '--tb=short'])
        else:
            base_cmd.extend([f'tests/{suite}', '-v', '--tb=short'])

        if coverage:
            base_cmd.extend(['--cov=src/soar_lab', '--cov-report=json'])

        result = asyncio.run(self._run_async(base_cmd))

        return {
            'status': 'success' if result['returncode'] == 0 else 'error',
            'output': result['stdout'],
            'error': result['stderr'],
            'duration': result['duration'],
            'returncode': result['returncode']
        }

    async def run_suite_async(self, suite: str, coverage: bool = True) -> Dict[str, Any]:
        """Run a test suite and return results (async version for FastAPI)."""
        base_cmd = ['python', '-m', 'pytest']

        if suite == "all":
            base_cmd.extend(['tests/', '-v', '--tb=short'])
        else:
            base_cmd.extend([f'tests/{suite}', '-v', '--tb=short'])

        if coverage:
            base_cmd.extend(['--cov=src/soar_lab', '--cov-report=json'])

        result = await self._run_async(base_cmd)

        return {
            'status': 'success' if result['returncode'] == 0 else 'error',
            'output': result['stdout'],
            'error': result['stderr'],
            'duration': result['duration'],
            'returncode': result['returncode']
        }

    def get_coverage(self) -> Dict[str, float]:
        """Get current test coverage from coverage.json."""
        coverage_file = self._path_service.coverage_file

        if not coverage_file.exists():
            return {"unit": 0, "integration": 0, "overall": 0}

        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)

        return {
            "unit": coverage_data.get('totals', {}).get('percent_covered', 0),
            "integration": 0,
            "overall": coverage_data.get('totals', {}).get('percent_covered', 0)
        }

    async def _run_async(self, cmd: list) -> Dict[str, Any]:
        """Run command asynchronously."""
        import time
        t0 = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self._repo_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
            duration = time.monotonic() - t0

            return {
                'returncode': proc.returncode or 0,
                'stdout': stdout_b.decode('utf-8', errors='ignore'),
                'stderr': stderr_b.decode('utf-8', errors='ignore'),
                'duration': duration
            }
        except asyncio.TimeoutError:
            logger.warning(f"Test suite timed out after {self._timeout}s")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'Timeout after {self._timeout}s',
                'duration': time.monotonic() - t0
            }
