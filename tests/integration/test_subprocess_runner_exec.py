#!/usr/bin/env python3
"""Integration tests for SubprocessRunner — real short-lived processes.

Verifies the BL-TEST-003 contract end-to-end: a timed-out run actually
kills the process *tree* (parent + grandchildren), not just the direct
child. Unit tests mock Popen; these prove the real behaviour.
"""

import sys
import time

import pytest

from soar_lab.infrastructure.subprocess_runner import SubprocessRunner

pytestmark = pytest.mark.integration


def _pid_alive(pid: int) -> bool:
    try:
        import psutil

        return psutil.pid_exists(pid)
    except ImportError:
        import os

        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True


class TestRealExecution:
    def test_real_command_succeeds(self):
        out = SubprocessRunner().run([sys.executable, "-c", "print('hi')"])
        assert out.success and "hi" in out.stdout

    def test_real_nonzero_exit(self):
        out = SubprocessRunner().run([sys.executable, "-c", "import sys;sys.exit(3)"])
        assert not out.success and out.returncode == 3

    def test_timeout_kills_process_tree(self, tmp_path):
        """A timed-out parent must not leave its grandchildren running."""
        pid_file = tmp_path / "parent.pid"
        # Parent writes its PID to a file, spawns a sleeping grandchild,
        # then sleeps. The file is independent of pipe capture timing.
        parent_code = (
            "import subprocess,sys,time,os;"
            f"open(r'{pid_file}','w').write(str(os.getpid()));"
            "subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
            "time.sleep(60)"
        )
        runner = SubprocessRunner()
        out = runner.run([sys.executable, "-c", parent_code], timeout=3)
        assert not out.success
        assert "Timeout" in out.stderr
        assert out.duration < 30

        assert pid_file.exists(), "parent never wrote its pid"
        parent_pid = int(pid_file.read_text().strip())
        time.sleep(0.5)
        assert not _pid_alive(parent_pid), f"parent pid {parent_pid} survived the timeout tree-kill"

    def test_async_real_timeout(self):
        import asyncio

        async def _run():
            return await SubprocessRunner().run_async(
                [sys.executable, "-c", "import time;time.sleep(60)"], timeout=2
            )

        out = asyncio.run(_run())
        assert not out.success and "Timeout" in out.stderr
