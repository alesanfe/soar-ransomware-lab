#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Subprocess Runner
Safe, consistent wrapper around subprocess.run / asyncio subprocess.
"""

import asyncio
import subprocess
import time
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.exceptions import SubprocessError

logger = get_logger(__name__)


class SubprocessResult:
    """Structured result from a subprocess execution."""

    __slots__ = ("success", "returncode", "stdout", "stderr", "duration")

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
        }


class SubprocessRunner:
    """Safe synchronous/async subprocess execution with consistent error handling."""

    def __init__(
            self,
            cwd: Optional[str] = None,
            default_timeout: int = 300,
    ) -> None:
        self.cwd = cwd
        self.default_timeout = default_timeout

    def run(
            self,
            cmd: List[str],
            timeout: Optional[int] = None,
            cwd: Optional[str] = None,
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
        try:
            proc = subprocess.run(
                cmd,
                cwd=effective_cwd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            duration = time.monotonic() - t0
            result = SubprocessResult(
                success=proc.returncode == 0,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration=duration,
            )
            if raise_on_error and not result.success:
                raise SubprocessError(cmd, proc.returncode, proc.stderr)
            return result
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {effective_timeout}s: {cmd}")
            return SubprocessResult(
                success=False,
                returncode=-1,
                stderr=f"Timeout after {effective_timeout}s",
                duration=time.monotonic() - t0,
            )
        except Exception as exc:
            logger.error(f"Unexpected error running {cmd}: {exc}")
            return SubprocessResult(
                success=False,
                returncode=-1,
                stderr=str(exc),
                duration=time.monotonic() - t0,
            )

    async def run_async(
            self,
            cmd: List[str],
            timeout: Optional[int] = None,
            cwd: Optional[str] = None,
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
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=effective_timeout
            )
            duration = time.monotonic() - t0
            stdout = stdout_b.decode("utf-8", errors="ignore")
            stderr = stderr_b.decode("utf-8", errors="ignore")
            result = SubprocessResult(
                success=proc.returncode == 0,
                returncode=proc.returncode or 0,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
            )
            if raise_on_error and not result.success:
                raise SubprocessError(cmd, proc.returncode or -1, stderr)
            return result
        except asyncio.TimeoutError:
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
            logger.error(f"Unexpected async error running {cmd}: {exc}")
            return SubprocessResult(
                success=False,
                returncode=-1,
                stderr=str(exc),
                duration=time.monotonic() - t0,
            )
