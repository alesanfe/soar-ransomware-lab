#!/usr/bin/env python3
"""Unit tests for pytest_test_runner.py."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from soar_lab.infrastructure.pytest_test_runner import PytestTestRunner, TestRunResult

pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")


class TestPytestTestRunner:
    """Test PytestTestRunner infrastructure adapter."""

    def test_initialization_success(self):
        """Test successful initialization."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()

        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        assert runner._repo_root == repo_root
        assert runner._path_service == mock_path_service
        assert runner._timeout == 300

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()

        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service, timeout=600)

        assert runner._timeout == 600

    def test_requires_repo_root(self):
        """Test that repo_root is required."""
        with pytest.raises(ValueError, match="repo_root is required"):
            PytestTestRunner(repo_root=None, path_service=Mock())

    def test_requires_path_service(self):
        """Test that path_service is required."""
        with pytest.raises(ValueError, match="path_service is required"):
            PytestTestRunner(repo_root=Path("/test"), path_service=None)

    @patch("soar_lab.infrastructure.pytest_test_runner.asyncio.run")
    def test_run_suite_all(self, mock_asyncio_run):
        """Test run_suite with 'all' suite."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_asyncio_run.return_value = TestRunResult(
            returncode=0, stdout="test output", stderr="", duration=5.0
        )
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.run_suite("all", coverage=False)

        assert result["status"] == "success"
        assert result["output"] == "test output"
        assert result["duration"] == 5.0

    @patch("soar_lab.infrastructure.pytest_test_runner.asyncio.run")
    def test_run_suite_specific(self, mock_asyncio_run):
        """Test run_suite with specific suite."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_asyncio_run.return_value = TestRunResult(
            returncode=0, stdout="test output", stderr="", duration=5.0
        )
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.run_suite("unit", coverage=False)

        assert result["status"] == "success"

    @patch("soar_lab.infrastructure.pytest_test_runner.asyncio.run")
    def test_run_suite_with_coverage(self, mock_asyncio_run):
        """Test run_suite with coverage enabled."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_asyncio_run.return_value = TestRunResult(
            returncode=0, stdout="test output", stderr="", duration=5.0
        )
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.run_suite("unit", coverage=True)

        assert result["status"] == "success"

    @patch("soar_lab.infrastructure.pytest_test_runner.asyncio.run")
    def test_run_suite_error(self, mock_asyncio_run):
        """Test run_suite with error return code."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_asyncio_run.return_value = TestRunResult(
            returncode=1, stdout="test output", stderr="error message", duration=5.0
        )
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.run_suite("unit", coverage=False)

        assert result["status"] == "error"
        assert result["returncode"] == 1
        assert result["error"] == "error message"

    def test_get_coverage_file_not_exists(self):
        """Test get_coverage when coverage file doesn't exist."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_coverage_file = Mock()
        mock_coverage_file.exists.return_value = False
        mock_path_service.coverage_file = mock_coverage_file
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.get_coverage()

        # Unmeasured coverage is explicit — never a fake 0%.
        assert result == {
            "unit": None,
            "integration": None,
            "overall": None,
            "measured": False,
        }

    @patch("builtins.open")
    def test_get_coverage_file_exists(self, mock_open):
        """Test get_coverage when coverage file exists."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_coverage_file = Mock()
        mock_coverage_file.exists.return_value = True
        mock_path_service.coverage_file = mock_coverage_file

        coverage_data = {"totals": {"percent_covered": 85.5}}
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_data)

        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.get_coverage()

        assert result["unit"] == 85.5
        assert result["overall"] == 85.5
        assert result["measured"] is True
        assert result["integration"] is None  # not measured per-suite

    @patch("builtins.open")
    def test_get_coverage_missing_totals(self, mock_open):
        """Test get_coverage when coverage file has no totals."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        mock_coverage_file = Mock()
        mock_coverage_file.exists.return_value = True
        mock_path_service.coverage_file = mock_coverage_file

        coverage_data = {}
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_data)

        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        result = runner.get_coverage()

        # Corrupt/incomplete coverage data reports as unmeasured.
        assert result["unit"] is None
        assert result["overall"] is None
        assert result["measured"] is False

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.pytest_test_runner.asyncio.create_subprocess_exec")
    async def test_run_async_success(self, mock_subprocess_exec):
        """Test _run_async successful execution."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"test output", b"")
        mock_subprocess_exec.return_value = mock_proc

        result = await runner._run_async(["python", "-m", "pytest"])

        assert result.returncode == 0
        assert result.stdout == "test output"
        assert result.duration >= 0

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.pytest_test_runner.asyncio.create_subprocess_exec")
    async def test_run_async_timeout(self, mock_subprocess_exec):
        """Test _run_async with timeout."""
        repo_root = Path("/test/repo")
        mock_path_service = Mock()
        runner = PytestTestRunner(repo_root=repo_root, path_service=mock_path_service, timeout=1)

        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = TimeoutError()
        mock_subprocess_exec.return_value = mock_proc

        result = await runner._run_async(["python", "-m", "pytest"])

        assert result.returncode == -1
        assert "Timeout" in result.stderr

    @pytest.mark.asyncio
    async def test_run_async_timeout_kills_child(self, tmp_path):
        """Bug: wait_for(communicate(), timeout) cancels the read but the
        spawned child keeps running — same leak class fixed in
        SubprocessRunner. The child must be terminated on timeout."""
        import sys
        import time

        import psutil

        marker = f"leak_{time.time_ns()}"
        runner = PytestTestRunner(repo_root=tmp_path, path_service=Mock(), timeout=1)

        procs_before = {
            p.pid
            for p in psutil.process_iter(["cmdline"])
            if p.info["cmdline"] and marker in " ".join(p.info["cmdline"])
        }

        result = await runner._run_async(
            [sys.executable, "-c", f"import time; time.sleep(60)  # {marker}"]
        )
        assert result.returncode == -1

        # give the OS a moment to reap
        for _ in range(20):
            leaked = [
                p
                for p in psutil.process_iter(["cmdline"])
                if p.info["cmdline"]
                and marker in " ".join(p.info["cmdline"])
                and p.pid not in procs_before
            ]
            if not leaked:
                break
            await asyncio.sleep(0.1)
        assert not leaked, f"child processes leaked: {[p.pid for p in leaked]}"
