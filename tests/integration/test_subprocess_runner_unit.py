#!/usr/bin/env python3
"""
Unit tests for subprocess_runner.py
Tests subprocess runner functionality
"""

import pytest
from unittest.mock import patch, MagicMock

from soar_lab.infrastructure.subprocess_runner import SubprocessRunner


class TestSubprocessRunner:
    """Test SubprocessRunner class"""

    def test_initialization(self):
        """Test runner initialization"""
        runner = SubprocessRunner(default_timeout=300)
        assert runner.default_timeout == 300

    def test_initialization_default_timeout(self):
        """Test runner initialization with default timeout"""
        runner = SubprocessRunner()
        assert runner.default_timeout == 300

    def test_initialization_with_cwd(self, tmp_path):
        """Test runner initialization with cwd"""
        runner = SubprocessRunner(cwd=tmp_path)
        assert runner.cwd == tmp_path

    @patch('subprocess.run')
    def test_run_success(self, mock_run):
        """Test running a command successfully"""
        from subprocess import CompletedProcess

        mock_result = CompletedProcess(
            args=["echo", "hello"],
            returncode=0,
            stdout="hello",
            stderr=""
        )
        mock_run.return_value = mock_result

        runner = SubprocessRunner(default_timeout=300)
        result = runner.run(["echo", "hello"])

        assert result.success == True
        assert result.returncode == 0
        assert "hello" in result.stdout

    @patch('subprocess.run')
    def test_run_with_timeout(self, mock_run):
        """Test running a command with timeout"""
        from subprocess import CompletedProcess

        mock_result = CompletedProcess(
            args=["echo", "test"],
            returncode=0,
            stdout="test",
            stderr=""
        )
        mock_run.return_value = mock_result

        runner = SubprocessRunner(default_timeout=5)
        result = runner.run(["echo", "test"])

        assert result.success == True

    @patch('subprocess.run')
    def test_run_failure(self, mock_run):
        """Test running a command that fails"""
        from subprocess import CompletedProcess

        mock_result = CompletedProcess(
            args=["false"],
            returncode=1,
            stdout="",
            stderr="error"
        )
        mock_run.return_value = mock_result

        runner = SubprocessRunner(default_timeout=300)
        result = runner.run(["false"])

        assert result.success == False
        assert result.returncode == 1

    @patch('subprocess.run')
    def test_run_with_cwd(self, mock_run, tmp_path):
        """Test running a command with custom working directory"""
        from subprocess import CompletedProcess

        mock_result = CompletedProcess(
            args=["pwd"],
            returncode=0,
            stdout=str(tmp_path),
            stderr=""
        )
        mock_run.return_value = mock_result

        runner = SubprocessRunner(default_timeout=300)
        result = runner.run(["pwd"], cwd=tmp_path)

        assert result.success == True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_raise_on_error_false(self, mock_run):
        """Test running a command with raise_on_error=False (default)"""
        from subprocess import CompletedProcess

        mock_result = CompletedProcess(
            args=["false"],
            returncode=1,
            stdout="",
            stderr="error"
        )
        mock_run.return_value = mock_result

        runner = SubprocessRunner(default_timeout=300)
        result = runner.run(["false"], raise_on_error=False)

        # Should not raise, just return failure
        assert result.success == False

    @patch('subprocess.run')
    def test_run_timeout_expired(self, mock_run):
        """Test running a command that times out"""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired(["echo"], 5)

        runner = SubprocessRunner(default_timeout=5)
        result = runner.run(["echo", "test"])

        assert result.success == False
        assert result.returncode == -1
        assert "Timeout" in result.stderr

    @patch('subprocess.run')
    def test_run_exception(self, mock_run):
        """Test running a command that raises an exception"""
        mock_run.side_effect = Exception("Unexpected error")

        runner = SubprocessRunner(default_timeout=300)
        result = runner.run(["echo", "test"])

        assert result.success == False
        assert result.returncode == -1
        assert "Unexpected error" in result.stderr

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_async_success(self, mock_subprocess_exec):
        """Test running a command asynchronously successfully"""
        from unittest.mock import AsyncMock

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"hello", b"")
        mock_subprocess_exec.return_value = mock_proc

        runner = SubprocessRunner(default_timeout=300)
        result = await runner.run_async(["echo", "hello"])

        assert result.success == True
        assert result.returncode == 0
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_async_failure(self, mock_subprocess_exec):
        """Test running a command asynchronously that fails"""
        from unittest.mock import AsyncMock

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"error")
        mock_subprocess_exec.return_value = mock_proc

        runner = SubprocessRunner(default_timeout=300)
        result = await runner.run_async(["false"])

        assert result.success == False
        assert result.returncode == 1
        assert "error" in result.stderr

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_async_timeout(self, mock_subprocess_exec):
        """Test running a command asynchronously that times out"""
        from unittest.mock import AsyncMock
        import asyncio

        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = asyncio.TimeoutError()
        mock_subprocess_exec.return_value = mock_proc

        runner = SubprocessRunner(default_timeout=5)
        result = await runner.run_async(["echo", "test"])

        assert result.success == False
        assert result.returncode == -1
        assert "Timeout" in result.stderr

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_async_exception(self, mock_subprocess_exec):
        """Test running a command asynchronously that raises an exception"""
        from unittest.mock import AsyncMock

        mock_subprocess_exec.side_effect = Exception("Unexpected error")

        runner = SubprocessRunner(default_timeout=300)
        result = await runner.run_async(["echo", "test"])

        assert result.success == False
        assert result.returncode == -1
        assert "Unexpected error" in result.stderr

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_async_raise_on_error_true(self, mock_subprocess_exec):
        """Test running a command asynchronously with raise_on_error=True"""
        from unittest.mock import AsyncMock
        from soar_lab.common.exceptions import SubprocessError

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"error")
        mock_subprocess_exec.return_value = mock_proc

        runner = SubprocessRunner(default_timeout=300)

        with pytest.raises(SubprocessError):
            await runner.run_async(["false"], raise_on_error=True)

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_async_with_cwd(self, mock_subprocess_exec):
        """Test running a command asynchronously with custom working directory"""
        from unittest.mock import AsyncMock

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"test", b"")
        mock_subprocess_exec.return_value = mock_proc

        runner = SubprocessRunner(default_timeout=300)
        result = await runner.run_async(["pwd"], cwd="/tmp")

        assert result.success == True
        mock_subprocess_exec.assert_called_once()

    def test_subprocess_result_to_dict(self):
        """Test SubprocessResult to_dict method"""
        from soar_lab.infrastructure.subprocess_runner import SubprocessResult

        result = SubprocessResult(
            success=True,
            returncode=0,
            stdout="output",
            stderr="error",
            duration=1.5
        )

        result_dict = result.to_dict()

        assert result_dict["success"] == True
        assert result_dict["returncode"] == 0
        assert result_dict["stdout"] == "output"
        assert result_dict["stderr"] == "error"
        assert result_dict["duration"] == 1.5
