import signal
import threading
import time
from typing import Any, Callable, Optional


class TimeoutError(Exception):
    pass


class TimeoutHandler:
    def __init__(self, timeout: float = 5.0, default_timeout: Optional[float] = None) -> None:
        self.timeout = default_timeout if default_timeout is not None else timeout
        self.default_timeout = self.timeout

    def run(self, func: Callable, *args, **kwargs):
        return self.execute_with_timeout(func, timeout=self.timeout, *args, **kwargs)

    def execute_with_timeout(
        self,
        func: Callable,
        timeout: Optional[float] = None,
        cleanup: Optional[Callable[[], None]] = None,
        on_timeout: Optional[Callable[[], None]] = None,
        *args,
        **kwargs,
    ) -> Any:
        deadline = timeout or self.default_timeout or self.timeout
        result: Any = None
        error: Optional[BaseException] = None
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
            if cleanup is not None:
                try:
                    cleanup()
                except Exception:
                    pass
            if on_timeout is not None:
                try:
                    on_timeout()
                except Exception:
                    pass
            raise TimeoutError("Operation timed out")

        if error is not None:
            raise error
        return result


def _timeout_signal_handler(signum, frame):
    raise TimeoutError("Operation timed out")


class _TimeoutContext:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self._timer: Optional[threading.Timer] = None
        self._old_handler = None
        self._signum = getattr(signal, "SIGBREAK", None)
        if self._signum is None:
            self._signum = getattr(signal, "SIGALRM", None)

    def __enter__(self):
        if self._signum is None:
            return self
        self._old_handler = signal.signal(self._signum, _timeout_signal_handler)
        self._timer = threading.Timer(self.timeout, signal.raise_signal, args=(self._signum,))
        self._timer.daemon = True
        self._timer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._timer is not None:
            self._timer.cancel()
        if self._signum is not None and self._old_handler is not None:
            signal.signal(self._signum, self._old_handler)
        return False


def timeout_context(timeout: float = 5.0):
    return _TimeoutContext(timeout)
