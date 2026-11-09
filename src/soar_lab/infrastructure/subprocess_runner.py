#!/usr/bin/env python3
"""SOAR Ransomware Lab - Subprocess Runner.

Safe, consistent wrapper around subprocess.run / asyncio subprocess.
"""

import asyncio
import contextlib
import os
import signal
import subprocess
import time
from typing import Any

import psutil

from soar_lab.common.constants import DEFAULT_TEST_TIMEOUT
from soar_lab.common.exceptions import SubprocessError
from soar_lab.config.logging import get_logger

__all__ = ["SubprocessResult", "SubprocessRunner"]

logger = get_logger(__name__)


def _kill_process_tree(pid: int) -> None:
    """Kill *pid* and all its descendants (best-effort).

    ``subprocess`` timeout handling only kills the direct child — a
    process like ``pytest`` that spawned its own children would leave
    orphans running after the timeout. Uses psutil's recursive children
    walk; falls back to killing just the pid if psutil fails.
    """
    try:

        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                child.kill()
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            parent.kill()
    except Exception:
        with contextlib.suppress(ProcessLookupError, OSError):

            sig = signal.SIGTERM if os.name == "nt" else signal.SIGKILL  # pylint: disable=no-member
            os.kill(pid, sig)


class SubprocessResult:
    """Structured result from a subprocess execution."""

    __slots__ = ("duration", "returncode", "stderr", "stdout", "success")

    def __init__(
        self,
        *,
        success: bool,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
        duration: float = 0.0,
    ) -> None:
        self.success = success
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
        }


class SubprocessRunner:
    """Safe synchronous/async subprocess execution with consistent error.

    handling.
    """

    def __init__(
        self,
        cwd: str | None = None,
        default_timeout: int = DEFAULT_TEST_TIMEOUT,
    ) -> None:
        self.cwd = cwd
        self.default_timeout = default_timeout

    def run(
        self,
        cmd: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
        raise_on_error: bool = False,
    ) -> SubprocessResult:
        """Run *cmd* synchronously.

        Args:
            cmd: Command and arguments list.
            timeout: Override default timeout (seconds).
            cwd: Override default working directory.
            raise_on_error: If True, raise SubprocessError on non-zero exit.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout
        effective_cwd = cwd or self.cwd
        t0 = time.monotonic()
        proc: subprocess.Popen | None = None
        try:
            # pylint: disable-next=consider-using-with
            proc = subprocess.Popen(
                cmd,
                cwd=effective_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=effective_timeout)
            duration = time.monotonic() - t0
            returncode = proc.returncode if proc.returncode is not None else -1
            result = SubprocessResult(
                success=returncode == 0,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
            )
            if raise_on_error and not result.success:
                raise SubprocessError(cmd, returncode, stderr)
            return result
        except subprocess.TimeoutExpired as exc:
            logger.warning(f"Command timed out after {effective_timeout}s: {cmd}")
            if proc is not None:
                _kill_process_tree(proc.pid)
                with contextlib.suppress(Exception):
                    proc.wait(timeout=5)

            # Preserve partial output — the pipe often holds the cause of
            # the hang; discarding it makes timeouts undebuggable.
            def _to_str(chunks):
                if isinstance(chunks, (list, tuple)):
                    chunks = b"".join(
                        c if isinstance(c, bytes) else str(c).encode() for c in chunks
                    )
                if isinstance(chunks, bytes):
                    return chunks.decode("utf-8", errors="ignore")
                return chunks or ""

            partial_out = _to_str(exc.output or exc.stdout)
            partial_err = _to_str(exc.stderr)
            return SubprocessResult(
                success=False,
                returncode=-1,
                stdout=partial_out,
                stderr=partial_err or f"Timeout after {effective_timeout}s",
                duration=time.monotonic() - t0,
            )
        except SubprocessError:
            raise
        except Exception as exc:
            logger.exception(f"Unexpected error running {cmd}")
            return SubprocessResult(
                success=False,
                returncode=-1,
                stderr=str(exc),
                duration=time.monotonic() - t0,
            )

    async def run_async(
        self,
        cmd: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
        raise_on_error: bool = False,
    ) -> SubprocessResult:
        """Run *cmd* asynchronously.

        Args:
            cmd: Command and arguments list.
            timeout: Override default timeout (seconds).
            cwd: Override default working directory.
            raise_on_error: If True, raise SubprocessError on non-zero exit.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout
        effective_cwd = cwd or self.cwd or ""
        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=effective_cwd or None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=effective_timeout
                )
            except TimeoutError:
                _kill_process_tree(proc.pid)
                await proc.wait()
                raise
            duration = time.monotonic() - t0
            stdout = stdout_b.decode("utf-8", errors="ignore")
            stderr = stderr_b.decode("utf-8", errors="ignore")
            result = SubprocessResult(
                success=proc.returncode == 0,
                returncode=proc.returncode if proc.returncode is not None else -1,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
            )
            if raise_on_error and not result.success:
                raise SubprocessError(cmd, result.returncode, stderr)
            return result
        except TimeoutError:
            logger.warning(f"Async command timed out after {effective_timeout}s: {cmd}")
            return SubprocessResult(
                success=False,
                returncode=-1,
                stderr=f"Timeout after {effective_timeout}s",
                duration=time.monotonic() - t0,
            )
        except SubprocessError:
            raise
        except Exception as exc:
            logger.exception(f"Unexpected async error running {cmd}")
            return SubprocessResult(
                success=False,
                returncode=-1,
                stderr=str(exc),
                duration=time.monotonic() - t0,
            )
