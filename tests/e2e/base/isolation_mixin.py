"""Isolation mixin for E2E tests (E2E-ISO-001 / E2E-TIME-001 / E2E-TIME-002).

Provides:
- ``run_id`` — short unique namespace for this test run.
- ``uid(prefix)`` — collision-proof identifier for alert_ids, hosts, keys.
- ``timeout(kind)`` — centralized timeout accessor (see timeouts.py).
- ``wait_until`` — generic bounded poll with backoff and last-state
  diagnostics (replaces ad-hoc ``time.sleep`` + loop patterns).
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable
from typing import Any

from .timeouts import timeout_for


class IsolationMixin:
    """Namespace, timeout and polling helpers shared by all E2E tests."""

    run_id: str
    POLL_INTERVAL: int

    def init_run_namespace(self) -> None:
        """Initialize the per-run namespace.

        Called from ``create_run_context`` — the ``run_id`` is a short
        uuid suffix (not a timestamp) so two parallel runs of the SAME
        test within one second cannot collide.
        """
        self.run_id = uuid.uuid4().hex[:8]

    def uid(self, prefix: str) -> str:
        """Return a unique ``{prefix}-{run_id}-{counter}`` identifier.

        Collision-free across calls within a run and across parallel runs.
        """
        if not getattr(self, "run_id", None):
            self.init_run_namespace()  # defensive: used before setup_method
        counter = getattr(self, "_uid_counter", 0) + 1
        self._uid_counter = counter
        return f"{prefix}-{self.run_id}-{counter}"

    def timeout(self, kind: str) -> int:
        """Centralized timeout accessor (E2E-TIME-002).

        Reads ``E2E_TIMEOUT_<KIND>`` env overrides, else the TIMEOUTS
        table.  Unknown kinds raise KeyError — inventing a timeout kind
        on the fly is exactly the drift this accessor exists to prevent.
        """
        env = getattr(self, "env", None) or {}
        merged = {**dict(os.environ), **env}
        return timeout_for(kind, merged)

    def wait_until(
        self,
        condition: Callable[[], Any],
        *,
        timeout: float | None = None,
        interval: float | None = None,
        backoff: float = 1.0,
        description: str = "condition",
        timeout_kind: str | None = None,
    ) -> Any:
        """Poll ``condition`` until truthy or the deadline expires.

        Args:
            condition: Zero-arg callable; its LAST returned value is
                included in the timeout message (diagnostics, TIME-001).
            timeout: Hard deadline in seconds.  If ``timeout_kind`` is
                given it overrides this via the centralized table.
            interval: Initial poll interval (default POLL_INTERVAL).
            backoff: Multiplicative backoff per iteration (1.0 = fixed).
            description: Human label used in the timeout message.
            timeout_kind: Optional TIMEOUTS key resolving ``timeout``.

        Returns:
            The truthy value returned by ``condition``.

        Raises:
            TimeoutError: Always on deadline — callers that want pytest
                semantics get a clear, stateful message either way.
        """
        if timeout_kind is not None:
            timeout = float(self.timeout(timeout_kind))
        if timeout is None:
            timeout = float(getattr(self, "WORKFLOW_TIMEOUT", 600))
        wait = float(interval if interval is not None else self.POLL_INTERVAL)
        deadline = time.monotonic() + timeout
        last: Any = None
        while True:
            last = condition()
            if last:
                return last
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timeout after {timeout:.0f}s waiting for {description}. "
                    f"Last state: {last!r}"
                )
            time.sleep(min(wait, max(0.0, deadline - time.monotonic())))
            wait *= backoff
