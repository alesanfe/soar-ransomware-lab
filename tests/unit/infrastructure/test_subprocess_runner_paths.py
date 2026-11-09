#!/usr/bin/env python3
"""Coverage tests for subprocess_runner.py error/kill paths — pure mocks.

The module's own ``subprocess`` reference is patched (no top-level
``import subprocess`` in this file, per the unit conftest boundary);
real process spawning lives in
``tests/integration/test_subprocess_runner_exec.py``.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

import soar_lab.infrastructure.subprocess_runner as sr
from soar_lab.common.exceptions import SubprocessError
from soar_lab.infrastructure.subprocess_runner import (
    SubprocessResult,
    SubprocessRunner,
    _kill_process_tree,
)


def _popen_mock(stdout="out", stderr="", returncode=0, communicate_effect=None):
    proc = Mock()
    if communicate_effect is not None:
        proc.communicate.side_effect = communicate_effect
    else:
        proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    proc.pid = 9999
    proc.wait.return_value = 0
    return proc


class TestSubprocessResult:
    def test_to_dict_roundtrip(self):
        r = SubprocessResult(success=True, returncode=0, stdout="o", stderr="e", duration=1.5)
        assert r.to_dict() == {
            "success": True,
            "returncode": 0,
            "stdout": "o",
            "stderr": "e",
            "duration": 1.5,
        }


class TestRunSync:
    def test_success(self):
        proc = _popen_mock(stdout="hi")
        with patch.object(sr.subprocess, "Popen", return_value=proc):
            out = SubprocessRunner().run(["x"])
        assert out.success and out.stdout == "hi"

    def test_nonzero_exit_not_error_by_default(self):
        proc = _popen_mock(returncode=3, stderr="bad")
        with patch.object(sr.subprocess, "Popen", return_value=proc):
            out = SubprocessRunner().run(["x"])
        assert not out.success and out.returncode == 3

    def test_raise_on_error_raises_subprocess_error(self):
        proc = _popen_mock(returncode=3, stderr="bad")
        with patch.object(sr.subprocess, "Popen", return_value=proc):
            with pytest.raises(SubprocessError):
                SubprocessRunner().run(["x"], raise_on_error=True)

    def test_timeout_kills_process_tree_and_returns_failure(self):
        timeout_exc = sr.subprocess.TimeoutExpired(cmd=["x"], timeout=1)
        proc = _popen_mock(communicate_effect=timeout_exc)
        with patch.object(sr.subprocess, "Popen", return_value=proc):
            with patch.object(sr, "_kill_process_tree") as kill:
                out = SubprocessRunner().run(["x"], timeout=1)
        kill.assert_called_once_with(9999)
        assert not out.success and out.returncode == -1
        assert "Timeout" in out.stderr

    def test_generic_exception_captured(self):
        with patch.object(sr.subprocess, "Popen", side_effect=OSError("no binary")):
            out = SubprocessRunner().run(["x"])
        assert not out.success and out.returncode == -1
        assert "no binary" in out.stderr

    def test_returncode_none_coerced_to_minus_one(self):
        proc = _popen_mock(returncode=None)
        with patch.object(sr.subprocess, "Popen", return_value=proc):
            out = SubprocessRunner().run(["x"])
        assert out.returncode == -1 and not out.success


class TestKillProcessTree:
    def test_psutil_path_kills_children_then_parent(self):
        fake_psutil = Mock()
        parent = Mock()
        child = Mock()
        parent.children.return_value = [child]
        fake_psutil.Process.return_value = parent
        fake_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        fake_psutil.AccessDenied = type("AccessDenied", (Exception,), {})
        with patch.object(sr, "psutil", fake_psutil):
            _kill_process_tree(1234)
        child.kill.assert_called_once()
        parent.kill.assert_called_once()

    def test_psutil_failure_falls_back_to_os_kill(self):
        kill_calls = []
        fake_psutil = Mock()
        fake_psutil.Process.side_effect = RuntimeError("psutil broken")
        with patch.object(sr, "psutil", fake_psutil):
            with patch("os.kill", lambda pid, sig: kill_calls.append((pid, sig))):
                _kill_process_tree(4321)
        assert kill_calls and kill_calls[0][0] == 4321


class TestRunAsync:
    async def test_async_success(self):
        proc = Mock()
        proc.communicate = AsyncMock(return_value=(b"hi", b""))
        proc.returncode = 0
        proc.pid = 9999
        with patch.object(sr.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)):
            out = await SubprocessRunner().run_async(["x"])
        assert out.success and out.stdout == "hi"

    async def test_async_nonzero_and_raise_on_error(self):
        proc = Mock()
        proc.communicate = AsyncMock(return_value=(b"", b"err"))
        proc.returncode = 4
        with patch.object(sr.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)):
            out = await SubprocessRunner().run_async(["x"])
            assert not out.success and out.returncode == 4
            with pytest.raises(SubprocessError):
                await SubprocessRunner().run_async(["x"], raise_on_error=True)

    async def test_async_timeout_kills_tree(self):
        proc = Mock()
        proc.communicate = AsyncMock(side_effect=TimeoutError())
        proc.wait = AsyncMock(return_value=0)
        proc.pid = 9999
        with patch.object(sr.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)):
            with patch.object(sr, "_kill_process_tree") as kill:
                out = await SubprocessRunner().run_async(["x"], timeout=1)
        kill.assert_called_once_with(9999)
        assert not out.success and out.returncode == -1
        assert "Timeout" in out.stderr

    async def test_async_generic_exception_captured(self):
        with patch.object(
            sr.asyncio,
            "create_subprocess_exec",
            AsyncMock(side_effect=OSError("no binary")),
        ):
            out = await SubprocessRunner().run_async(["x"])
        assert not out.success and out.returncode == -1
        assert "no binary" in out.stderr
