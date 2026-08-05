"""Lightweight transaction abstraction used by unit tests and small services."""

import threading
import time
from typing import Any, Callable, List, Optional, Type


class Transaction:
    """In-memory transaction with isolation level and savepoint support."""

    def __init__(self, isolation_level: Optional[str] = None) -> None:
        self.isolation_level = isolation_level
        self.operations: List[str] = []
        self.savepoints: dict = {}
        self._committed = False
        self._rolled_back = False

    def execute(self, statement: str) -> None:
        self.operations.append(statement)

    def commit(self) -> bool:
        self._committed = True
        return True

    def rollback(self) -> None:
        self.operations.clear()
        self._rolled_back = True

    def set_isolation_level(self, level: str) -> None:
        self.isolation_level = level

    def create_savepoint(self, name: str) -> None:
        self.savepoints[name] = list(self.operations)

    def rollback_to_savepoint(self, name: str) -> None:
        if name in self.savepoints:
            self.operations = list(self.savepoints[name])


class TransactionManager:
    """Factory and context manager for Transaction objects."""

    _local = threading.local()

    def begin(self, isolation_level: Optional[str] = None) -> Transaction:
        tx = Transaction(isolation_level=isolation_level)
        if isolation_level:
            tx.set_isolation_level(isolation_level)
        return tx

    def atomic(
        self,
        timeout: Optional[float] = None,
        isolation_level: Optional[str] = None,
    ):
        """Return a context manager that auto-commits or rolls back."""
        return _AtomicContext(self, timeout, isolation_level)

    def execute_with_retry(
        self,
        func: Callable[[], Any],
        max_retries: int = 3,
        retry_on: Optional[List[Exception]] = None,
    ) -> Any:
        retry_on = retry_on or []
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as exc:
                last_exc = exc
                if attempt >= max_retries:
                    break
                if not retry_on:
                    continue
                matched = False
                for ref in retry_on:
                    if isinstance(exc, type(ref)):
                        if str(ref) and str(ref) not in str(exc):
                            continue
                        matched = True
                        break
                if not matched:
                    break
                time.sleep(0.01)
        raise last_exc


class _AtomicContext:
    def __init__(
        self,
        manager: TransactionManager,
        timeout: Optional[float] = None,
        isolation_level: Optional[str] = None,
    ) -> None:
        self.manager = manager
        self.timeout = timeout
        self.isolation_level = isolation_level
        self.transaction: Optional[Transaction] = None

    def __enter__(self) -> Transaction:
        self.transaction = self.manager.begin(isolation_level=self.isolation_level)
        return self.transaction

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.transaction is None:
            return
        if exc_val is not None:
            self.transaction.rollback()
            return
        if self.timeout:
            import threading

            result = {"done": False, "error": None}

            def _commit():
                try:
                    self.transaction.commit()
                    result["done"] = True
                except Exception as e:
                    result["error"] = e

            t = threading.Thread(target=_commit, daemon=True)
            t.start()
            t.join(timeout=self.timeout)
            if not result["done"]:
                raise TimeoutError(
                    f"Transaction commit did not complete within {self.timeout}s"
                )
            if result["error"]:
                raise result["error"]
        else:
            self.transaction.commit()
