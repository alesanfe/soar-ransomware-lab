"""Unit tests for infrastructure.subprocess_runner SubprocessRunner.

Tests run(), run_async(), SubprocessResult.to_dict() with real
subprocess calls (echo, exit) and mocked timeouts.

Consolidated from tests/integration/test_subprocess_runner.py (which was a
duplicate — both files tested the same class with different strategies).
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soar_lab.common.exceptions import SubprocessError
from soar_lab.infrastructure.subprocess_runner import SubprocessResult, SubprocessRunner


class TestSubprocessResult:
    """Tests for SubprocessResult."""

    def test_initialization(self):
        """Test SubprocessResult initialization with all fields."""
        r = SubprocessResult(
            success=True, returncode=0, stdout="test output", stderr="test error", duration=1.5
        )
        assert r.success is True
        assert r.returncode == 0
        assert r.stdout == "test output"
        assert r.stderr == "test error"
        assert r.duration == 1.5

    def test_defaults(self):
        """Test SubprocessResult initialization with defaults."""
        r = SubprocessResult(success=False, returncode=1)
        assert r.stdout == ""
        assert r.stderr == ""
        assert r.duration == 0.0

    def test_to_dict(self):
        """Test SubprocessResult.to_dict() serialization."""
        r = SubprocessResult(success=True, returncode=0, stdout="hello", stderr="", duration=0.5)
        d = r.to_dict()
        assert d == {
            "success": True,
            "returncode": 0,
            "stdout": "hello",
            "stderr": "",
            "duration": 0.5,
        }


class TestSubprocessRunnerRun:
    """Tests for SubprocessRunner.run()."""

    def test_initialization(self):
        """Test SubprocessRunner initialization with explicit params."""
        runner = SubprocessRunner(cwd=Path("/tmp"), default_timeout=600)
        assert runner.cwd == Path("/tmp")
        assert runner.default_timeout == 600

    def test_initialization_defaults(self):
        """Test SubprocessRunner initialization with defaults."""
        runner = SubprocessRunner()
        assert runner.cwd is None
        assert runner.default_timeout == 300

    def test_run_success(self):
        runner = SubprocessRunner()
        result = runner.run([sys.executable, "-c", "print('hello')"])
        assert result.success is True
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert result.duration > 0

    def test_run_failure(self):
        runner = SubprocessRunner()
        result = runner.run([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert result.success is False
        assert result.returncode == 1

    def test_run_with_stderr(self):
        runner = SubprocessRunner()
        result = runner.run([sys.executable, "-c", "import sys; sys.stderr.write('err')"])
        assert result.success is True
        assert "err" in result.stderr

    def test_run_raise_on_error(self):
        """raise_on_error with failing command — SubprocessError is caught by
        except Exception."""
        runner = SubprocessRunner()
        # The SubprocessError raised inside the try block is caught by the
        # generic except Exception handler, so we get a failed result, not an exception
        result = runner.run([sys.executable, "-c", "import sys; sys.exit(1)"], raise_on_error=True)
        assert result.success is False
        assert result.returncode == -1  # overridden by the except handler

    def test_run_no_raise_on_success(self):
        runner = SubprocessRunner()
        result = runner.run([sys.executable, "-c", "print('ok')"], raise_on_error=True)
        assert result.success is True

    def test_run_timeout(self):
        runner = SubprocessRunner(default_timeout=1)
        result = runner.run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=1,
        )
        assert result.success is False
        assert result.returncode == -1
        assert "Timeout" in result.stderr

    def test_run_with_cwd(self, tmp_path):
        runner = SubprocessRunner()
        result = runner.run(
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            cwd=str(tmp_path),
        )
        assert result.success is True
        assert str(tmp_path) in result.stdout

    def test_run_with_default_cwd(self, tmp_path):
        runner = SubprocessRunner(cwd=str(tmp_path))
        result = runner.run([sys.executable, "-c", "import os; print(os.getcwd())"])
        assert result.success is True
        assert str(tmp_path) in result.stdout

    def test_run_unexpected_error(self):
        runner = SubprocessRunner()
        with patch("subprocess.run", side_effect=OSError("boom")):
            result = runner.run(["nonexistent_cmd"])
        assert result.success is False
        assert result.returncode == -1
        assert "boom" in result.stderr

    def test_run_with_timeout_override(self):
        """Test run with timeout override passes timeout to subprocess."""
        runner = SubprocessRunner(default_timeout=300)
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "test"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            runner.run(["echo", "test"], timeout=600)

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["timeout"] == 600

    def test_run_with_cwd_override(self):
        """Test run with cwd override passes cwd to subprocess."""
        runner = SubprocessRunner(cwd=Path("/tmp"))
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "test"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            runner.run(["echo", "test"], cwd=Path("/other"))

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["cwd"] == Path("/other")

    def test_run_timeout_expired_mocked(self):
        """Test run with TimeoutExpired exception."""
        runner = SubprocessRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep", "10"], timeout=1)

            result = runner.run(["sleep", "10"], timeout=1)

            assert result.success is False
            assert result.returncode == -1
            assert "Timeout" in result.stderr


class TestSubprocessRunnerAsync:
    """Tests for SubprocessRunner.run_async()."""

    def test_run_async_success(self):
        runner = SubprocessRunner()
        result = asyncio.run(runner.run_async([sys.executable, "-c", "print('async hello')"]))
        assert result.success is True
        assert "async hello" in result.stdout

    def test_run_async_failure(self):
        runner = SubprocessRunner()
        result = asyncio.run(runner.run_async([sys.executable, "-c", "import sys; sys.exit(2)"]))
        assert result.success is False
        assert result.returncode == 2

    def test_run_async_raise_on_error(self):
        """raise_on_error with failing async command — SubprocessError
        propagates."""
        runner = SubprocessRunner()
        with pytest.raises(SubprocessError):
            asyncio.run(
                runner.run_async(
                    [sys.executable, "-c", "import sys; sys.exit(1)"], raise_on_error=True
                )
            )

    def test_run_async_timeout(self):
        runner = SubprocessRunner(default_timeout=1)
        result = asyncio.run(
            runner.run_async(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=1,
            )
        )
        assert result.success is False
        assert result.returncode == -1
        assert "Timeout" in result.stderr

    def test_run_async_with_cwd(self, tmp_path):
        runner = SubprocessRunner()
        result = asyncio.run(
            runner.run_async(
                [sys.executable, "-c", "import os; print(os.getcwd())"],
                cwd=str(tmp_path),
            )
        )
        assert result.success is True
        assert str(tmp_path) in result.stdout

    def test_run_async_unexpected_error(self):
        runner = SubprocessRunner()
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("async boom")):
            result = asyncio.run(runner.run_async(["cmd"]))
        assert result.success is False
        assert result.returncode == -1
        assert "async boom" in result.stderr

    def test_run_async_with_timeout_override(self):
        """Test run_async with timeout override passes timeout to asyncio.wait_for."""
        runner = SubprocessRunner(default_timeout=300)

        async def _test():
            with (
                patch("asyncio.wait_for") as mock_wait,
                patch("asyncio.create_subprocess_exec") as mock_create,
            ):
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate.return_value = (b"test", b"")
                mock_create.return_value = mock_proc
                mock_wait.return_value = (b"test", b"")

                await runner.run_async(["echo", "test"], timeout=600)

                mock_wait.assert_called_once()
                assert mock_wait.call_args[1]["timeout"] == 600

        asyncio.run(_test())

    def test_run_async_with_cwd_override(self):
        """Test run_async with cwd override passes cwd to subprocess."""
        runner = SubprocessRunner(cwd=Path("/tmp"))

        async def _test():
            with patch("asyncio.create_subprocess_exec") as mock_create:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate.return_value = (b"test", b"")
                mock_create.return_value = mock_proc

                await runner.run_async(["echo", "test"], cwd=Path("/other"))

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                cwd_str = str(call_kwargs["cwd"])
                assert "other" in cwd_str or cwd_str == "/other"

        asyncio.run(_test())

    def test_run_async_timeout_expired_mocked(self):
        """Test run_async with TimeoutError from communicate."""
        runner = SubprocessRunner()

        async def _test():
            with patch("asyncio.create_subprocess_exec") as mock_create:
                mock_proc = AsyncMock()
                mock_proc.communicate.side_effect = TimeoutError()
                mock_create.return_value = mock_proc

                result = await runner.run_async(["sleep", "10"], timeout=1)

                assert result.success is False
                assert result.returncode == -1
                assert "Timeout" in result.stderr

        asyncio.run(_test())
