"""Transactional cleanup for destructive E2E tests (E12-04).

Register undo actions as a test mutates shared state; ``run()`` unwinds
them in reverse order, attempting EVERY restore even when earlier steps
fail. The report distinguishes test failure vs cleanup failure so a
cleanup error never masks the original failure.

Usage::

    cleanup = CleanupStack()
    cleanup.push("restart soar_tempo", lambda: start_container("soar_tempo"))
    ...
    report = cleanup.run()
    if report.cleanup_errors:
        self._log(f"cleanup degraded: {report.cleanup_errors}")
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class CleanupReport:
    attempted: int = 0
    restored: int = 0
    cleanup_errors: list[str] = field(default_factory=list)


class CleanupStack:
    def __init__(self) -> None:
        self._stack: list[tuple[str, Callable[[], object]]] = []

    def push(self, label: str, undo: Callable[[], object]) -> None:
        """Register an undo action. Labels appear in the failure report."""
        self._stack.append((label, undo))

    def run(self) -> CleanupReport:
        """Unwind in reverse order; every step attempted despite failures."""
        rep = CleanupReport()
        while self._stack:
            label, undo = self._stack.pop()
            rep.attempted += 1
            try:
                undo()
                rep.restored += 1
            except Exception as e:  # noqa: BLE001 — cleanup must not raise
                rep.cleanup_errors.append(f"{label}: {e!r}")
                traceback.print_exc()
        return rep
