"""Timeout handling utilities for running operations with time limits."""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable
from typing import Any, Self

__all__ = ["TimeoutError", "TimeoutHandler", "timeout_context"]


class TimeoutError(Exception):
    """Raised when an operation exceeds its configured timeout."""


def _run_callback_safely(callback: Callable[[], None] | None) -> None:
    """Execute *callback* if provided, silently swallowing any exception.

    Args:
        callback: Optional callable to invoke, or None.
    """
    if callback is not None:
        try:
            callback()
        except Exception:
            pass


def _handle_timeout(
    cleanup: Callable[[], None] | None,
    on_timeout: Callable[[], None] | None,
) -> None:
    """Run cleanup and on_timeout callbacks then raise TimeoutError.

    Args:
        cleanup: Optional cleanup callable invoked before raising.
        on_timeout: Optional callback invoked before raising.

    Raises:
        TimeoutError: Always raised after callbacks complete.
    """
    _run_callback_safely(cleanup)
    _run_callback_safely(on_timeout)
    raise TimeoutError("Operation timed out")


class TimeoutHandler:
    """Runs callables with an enforced timeout using background threads."""

    def __init__(self, timeout: float = 5.0, default_timeout: float | None = None) -> None:
        """Initialize the TimeoutHandler with the given timeout values.

        Args:
            timeout: Default timeout in seconds.
            default_timeout: Optional override for the default timeout.
        """
        self.timeout = default_timeout if default_timeout is not None else timeout
        self.default_timeout = self.timeout

    def run(self, func: Callable, *args: object, **kwargs: object) -> Any:
        """Run *func* with the handler's default timeout.

        Args:
            func: Callable to execute.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            TimeoutError: If the operation exceeds the timeout.
        """
        return self.execute_with_timeout(func, timeout=self.timeout, *args, **kwargs)

    def execute_with_timeout(
        self,
        func: Callable,
        timeout: float | None = None,
        cleanup: Callable[[], None] | None = None,
        on_timeout: Callable[[], None] | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """Execute *func* in a background thread with an enforced deadline.

        Args:
            func: Callable to execute.
            timeout: Timeout in seconds for this call; falls back to the
                handler default when None.
            cleanup: Optional callback invoked if the operation times out.
            on_timeout: Optional callback invoked if the operation times out.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            TimeoutError: If the operation does not complete within the deadline.
        """
        deadline = timeout or self.default_timeout or self.timeout
        result: Any = None
        error: BaseException | None = None
        completed = threading.Event()

        def target() -> None:
            nonlocal result, error
            try:
                result = func(*args, **kwargs)
            except BaseException as exc:
                error = exc
            finally:
                completed.set()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        if not completed.wait(timeout=deadline):
            _handle_timeout(cleanup, on_timeout)

        if error is not None:
            raise error
        return result


def _timeout_signal_handler(_signum: int, _frame: object) -> None:
    """Signal handler that raises TimeoutError when a timeout signal is received.

    Args:
        _signum: Signal number (unused).
        _frame: Current stack frame (unused).

    Raises:
        TimeoutError: Always raised to interrupt the operation.
    """
    raise TimeoutError("Operation timed out")


def _resolve_signum() -> int | None:
    """Resolve an appropriate signal number for timeout interrupts.

    Returns:
        SIGBREAK on Windows or SIGALRM on Unix, or None if neither is available.
    """
    signum = getattr(signal, "SIGBREAK", None)
    if signum is None:
        signum = getattr(signal, "SIGALRM", None)
    return signum


class _TimeoutContext:
    """Context manager that raises TimeoutError after a configured delay."""

    def __init__(self, timeout: float) -> None:
        """Initialize the _TimeoutContext with the given timeout.

        Args:
            timeout: Timeout in seconds before the signal is raised.
        """
        self.timeout = timeout
        self._timer: threading.Timer | None = None
        self._old_handler = None
        self._signum = _resolve_signum()

    def __enter__(self) -> Self:
        """Arm the timeout timer and install the signal handler.

        Returns:
            The context manager instance.
        """
        if self._signum is None:
            return self
        self._old_handler = signal.signal(self._signum, _timeout_signal_handler)
        self._timer = threading.Timer(self.timeout, signal.raise_signal, args=(self._signum,))
        self._timer.daemon = True
        self._timer.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Cancel the timer and restore the previous signal handler.

        Args:
            exc_type: Exception type raised within the block, if any.
            exc_val: Exception instance raised, if any.
            _exc_tb: Traceback object, if any.
        """
        if self._timer is not None:
            self._timer.cancel()
        if self._signum is not None and self._old_handler is not None:
            signal.signal(self._signum, self._old_handler)


def timeout_context(timeout: float = 5.0) -> _TimeoutContext:
    """Create a timeout context manager.

    Args:
        timeout: Timeout in seconds before the signal is raised.

    Returns:
        A ``_TimeoutContext`` instance for use as a context manager.
    """
    return _TimeoutContext(timeout)
