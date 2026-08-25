"""Lightweight transaction abstraction used by unit tests and small.

services.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

__all__ = ["Transaction", "TransactionManager"]


class Transaction:
    """In-memory transaction with isolation level and savepoint support."""

    def __init__(self, isolation_level: str | None = None) -> None:
        """Initialize the Transaction with an optional isolation level.

        Args:
            isolation_level: Optional isolation level name (e.g. ``"serializable"``).
        """
        self.isolation_level = isolation_level
        self.operations: list[str] = []
        self.savepoints: dict = {}
        self._committed = False
        self._rolled_back = False

    def execute(self, statement: str) -> None:
        """Record a statement in the transaction's operation list.

        Args:
            statement: SQL or operation string to record.
        """
        self.operations.append(statement)

    def commit(self) -> bool:
        """Mark the transaction as committed.

        Returns:
            True indicating a successful commit.
        """
        self._committed = True
        return True

    def rollback(self) -> None:
        """Roll back the transaction by clearing all recorded operations."""
        self.operations.clear()
        self._rolled_back = True

    def set_isolation_level(self, level: str) -> None:
        """Set the isolation level for this transaction.

        Args:
            level: Isolation level name to apply.
        """
        self.isolation_level = level

    def create_savepoint(self, name: str) -> None:
        """Create a savepoint with the current operations snapshot.

        Args:
            name: Savepoint identifier.
        """
        self.savepoints[name] = list(self.operations)

    def rollback_to_savepoint(self, name: str) -> None:
        """Restore operations to the named savepoint.

        Args:
            name: Savepoint identifier to roll back to.
        """
        if name in self.savepoints:
            self.operations = list(self.savepoints[name])


class TransactionManager:
    """Factory and context manager for Transaction objects."""

    _local = threading.local()

    def begin(self, isolation_level: str | None = None) -> Transaction:
        """Begin a new transaction with an optional isolation level.

        Args:
            isolation_level: Optional isolation level to apply.

        Returns:
            A new Transaction instance.
        """
        tx = Transaction(isolation_level=isolation_level)
        if isolation_level:
            tx.set_isolation_level(isolation_level)
        return tx

    def atomic(
        self,
        timeout: float | None = None,
        isolation_level: str | None = None,
    ) -> "_AtomicContext":
        """Return a context manager that auto-commits or rolls back."""
        return _AtomicContext(self, timeout, isolation_level)

    def execute_with_retry(
        self,
        func: Callable[[], Any],
        max_retries: int = 3,
        retry_on: list[Exception] | None = None,
    ) -> Any:
        """Execute *func* with retry logic on matching exceptions.

        Args:
            func: Callable to execute.
            max_retries: Maximum number of retry attempts.
            retry_on: Optional list of exception instances to match for retry.

        Returns:
            The return value of *func*.

        Raises:
            Exception: The last exception if all retries are exhausted.
        """
        retry_on = retry_on or []
        last_exc: Exception | None = None
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
    """Context manager that auto-commits or rolls back a transaction."""

    def __init__(
        self,
        manager: TransactionManager,
        timeout: float | None = None,
        isolation_level: str | None = None,
    ) -> None:
        """Initialize the _AtomicContext with the given manager and options.

        Args:
            manager: TransactionManager used to begin the transaction.
            timeout: Optional commit timeout in seconds.
            isolation_level: Optional isolation level for the transaction.
        """
        self.manager = manager
        self.timeout = timeout
        self.isolation_level = isolation_level
        self.transaction: Transaction | None = None

    def __enter__(self) -> Transaction:
        """Begin and return a new transaction."""
        self.transaction = self.manager.begin(isolation_level=self.isolation_level)
        return self.transaction

    def __exit__(self, exc_type, exc_val, _exc_tb) -> None:
        """Commit or roll back the transaction on context exit.

        Args:
            exc_type: Exception type raised within the block, if any.
            exc_val: Exception instance raised, if any.
            _exc_tb: Traceback object, if any.
        """
        if self.transaction is None:
            return
        if exc_val is not None:
            self.transaction.rollback()
            return
        if self.timeout:
            import threading

            result = {"done": False, "error": None}

            def _commit() -> None:
                """Commit the transaction in a background thread."""
                try:
                    self.transaction.commit()
                    result["done"] = True
                except Exception as e:
                    result["error"] = e

            t = threading.Thread(target=_commit, daemon=True)
            t.start()
            t.join(timeout=self.timeout)
            if not result["done"]:
                raise TimeoutError(f"Transaction commit did not complete within {self.timeout}s")
            error: BaseException | None = result["error"]
            if error is not None:
                raise error
        else:
            self.transaction.commit()
