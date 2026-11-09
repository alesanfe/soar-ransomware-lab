"""Bulkhead isolation (RES-03): bound concurrent work per resource.

A bulkhead caps how many calls may run concurrently against one
dependency and how many may queue waiting, so a slow or hung integration
(Cortex, TheHive, MISP, ES) cannot exhaust the process's outbound
capacity and starve the others.  Two layers:

- ``Bulkhead`` — per-integration limit (sync ``threading`` semaphore).
- ``GLOBAL_BULKHEAD`` — process-wide ceiling across all integrations.

When both levels are saturated the call fails fast with
``BulkheadFullError`` (retryable) instead of queueing unboundedly behind
a degraded dependency.
"""

# pylint: disable=consider-using-with,import-outside-toplevel
# Semaphore.acquire(timeout=...) has no `with` equivalent; asyncio is
# imported lazily so the semaphores bind to the caller's event loop.

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["AsyncBulkhead", "Bulkhead", "BulkheadFullError", "GLOBAL_BULKHEAD"]

T = TypeVar("T")


class BulkheadFullError(Exception):
    """Raised when a bulkhead rejects work — resource saturated (retryable)."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"bulkhead '{name}' saturated")


class Bulkhead:
    """Bounded-concurrency guard around a callable (sync).

    ``concurrent`` running calls max, plus up to ``queued`` waiting;
    beyond that, calls fail fast.  ``acquire_timeout`` bounds the wait so
    callers do not hang behind a degraded dependency.
    """

    def __init__(
        self,
        name: str,
        concurrent: int = 10,
        queued: int = 50,
        acquire_timeout: float = 5.0,
    ) -> None:
        if concurrent < 1 or queued < 0 or acquire_timeout <= 0:
            raise ValueError("concurrent >= 1, queued >= 0, acquire_timeout > 0 required")
        self.name = name
        self._slots = threading.BoundedSemaphore(concurrent)
        self._queue = threading.BoundedSemaphore(concurrent + queued)
        self.acquire_timeout = acquire_timeout
        self.concurrent = concurrent
        self.queued = queued

    def run(self, fn: Callable[[], T]) -> T:
        """Run *fn* inside the bulkhead, failing fast when saturated."""
        # Queue permit: enforces the total in-flight bound (run+wait).
        if not self._queue.acquire(timeout=self.acquire_timeout):
            raise BulkheadFullError(self.name)
        try:
            if not self._slots.acquire(timeout=self.acquire_timeout):
                raise BulkheadFullError(self.name)
            try:
                return fn()
            finally:
                self._slots.release()
        finally:
            self._queue.release()

    @property
    def in_flight(self) -> int:
        """Calls currently running or waiting (diagnostics)."""
        return (self.concurrent + self.queued) - self._queue._value


class AsyncBulkhead:
    """Async variant — ``asyncio.Semaphore``-backed, same semantics."""

    def __init__(
        self,
        name: str,
        concurrent: int = 10,
        queued: int = 50,
        acquire_timeout: float = 5.0,
    ) -> None:
        if concurrent < 1 or queued < 0 or acquire_timeout <= 0:
            raise ValueError("concurrent >= 1, queued >= 0, acquire_timeout > 0 required")
        self.name = name
        self.acquire_timeout = acquire_timeout
        self._slots: Any = None  # lazy asyncio.Semaphore (binds to the loop)
        self._queue: Any = None
        self._concurrent = concurrent
        self._queued = queued

    def _ensure(self) -> None:
        import asyncio

        if self._slots is None:
            self._slots = asyncio.Semaphore(self._concurrent)
            self._queue = asyncio.Semaphore(self._concurrent + self._queued)

    async def run(self, fn: Callable[[], Any]) -> Any:
        """Await *fn()* inside the bulkhead, failing fast when saturated."""
        import asyncio

        self._ensure()
        try:
            await asyncio.wait_for(self._queue.acquire(), timeout=self.acquire_timeout)
        except TimeoutError as exc:
            raise BulkheadFullError(self.name) from exc
        try:
            try:
                await asyncio.wait_for(self._slots.acquire(), timeout=self.acquire_timeout)
            except TimeoutError as exc:
                raise BulkheadFullError(self.name) from exc
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    return await result
                return result
            finally:
                self._slots.release()
        finally:
            self._queue.release()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


# Process-wide ceiling: no integration fan-out may hold more than this
# many concurrent outbound calls, whichever client issues them.
GLOBAL_BULKHEAD = Bulkhead(
    name="global-outbound",
    concurrent=_env_int("SOAR_BULKHEAD_GLOBAL", 64),
    queued=_env_int("SOAR_BULKHEAD_GLOBAL_QUEUE", 256),
    acquire_timeout=_env_int("SOAR_BULKHEAD_TIMEOUT", 5),
)
