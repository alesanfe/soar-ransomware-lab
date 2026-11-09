"""Tests for resilience bulkhead isolation (RES-03)."""

import threading
import time

import pytest

from soar_lab.resilience.bulkhead import AsyncBulkhead, Bulkhead, BulkheadFullError


class TestBulkhead:
    def test_runs_function_and_returns_result(self):
        assert Bulkhead("t").run(lambda: 42) == 42

    def test_bounds_concurrency(self):
        running = [0]
        peak = [0]
        b = Bulkhead("t", concurrent=3, queued=100, acquire_timeout=2.0)

        def work():
            running[0] += 1
            peak[0] = max(peak[0], running[0])
            time.sleep(0.05)
            running[0] -= 1

        threads = [threading.Thread(target=lambda: b.run(work)) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert peak[0] <= 3

    def test_fails_fast_when_queue_full(self):
        b = Bulkhead("t", concurrent=1, queued=0, acquire_timeout=0.05)
        gate = threading.Event()

        def holder():
            gate.wait(2.0)

        t1 = threading.Thread(target=lambda: b.run(holder))
        t1.start()
        time.sleep(0.05)
        with pytest.raises(BulkheadFullError):
            b.run(lambda: None)
        gate.set()
        t1.join()

    def test_bulkhead_full_error_is_retryable_signal(self):
        b = Bulkhead("saturated-x", concurrent=1, queued=0, acquire_timeout=0.05)
        gate = threading.Event()
        t1 = threading.Thread(target=lambda: b.run(lambda: gate.wait(2.0)))
        t1.start()
        time.sleep(0.05)
        with pytest.raises(BulkheadFullError, match="saturated-x"):
            b.run(lambda: None)
        gate.set()
        t1.join()

    def test_isolation_across_bulkheads(self):
        slow = Bulkhead("slow", concurrent=1, queued=0, acquire_timeout=0.05)
        fast = Bulkhead("fast", concurrent=1, queued=0, acquire_timeout=0.05)
        gate = threading.Event()
        t1 = threading.Thread(target=lambda: slow.run(lambda: gate.wait(2.0)))
        t1.start()
        time.sleep(0.05)
        # A different integration's bulkhead is unaffected.
        assert fast.run(lambda: "ok") == "ok"
        with pytest.raises(BulkheadFullError):
            slow.run(lambda: None)
        gate.set()
        t1.join()

    def test_invalid_params_rejected(self):
        with pytest.raises(ValueError):
            Bulkhead("x", concurrent=0)
        with pytest.raises(ValueError):
            Bulkhead("x", concurrent=1, queued=-1)
        with pytest.raises(ValueError):
            Bulkhead("x", concurrent=1, acquire_timeout=0)

    def test_exception_releases_slots(self):
        b = Bulkhead("t", concurrent=1, queued=0)
        with pytest.raises(RuntimeError):
            b.run(_raise)
        assert b.run(lambda: "ok") == "ok"


def _raise():
    raise RuntimeError("boom")


class TestAsyncBulkhead:
    @pytest.mark.asyncio
    async def test_runs_coroutine(self):
        async def coro():
            return 7

        assert await AsyncBulkhead("a").run(coro) == 7

    @pytest.mark.asyncio
    async def test_fails_fast_when_saturated(self):
        import asyncio

        b = AsyncBulkhead("a", concurrent=1, queued=0, acquire_timeout=0.05)

        async def holder():
            await asyncio.sleep(0.5)

        task = asyncio.ensure_future(b.run(holder))
        await asyncio.sleep(0.05)
        with pytest.raises(BulkheadFullError):
            await b.run(holder)
        task.cancel()


class TestBaseClientBulkhead:
    def test_client_has_bulkhead_and_503_on_saturation(self):
        from soar_lab.common.exceptions import IntegrationUnavailableError
        from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient

        client = BaseHTTPClient("http://localhost:1", api_key="k")
        client._bulkhead = Bulkhead("test", concurrent=1, queued=0, acquire_timeout=0.05)
        gate = threading.Event()
        t1 = threading.Thread(target=lambda: client._bulkhead.run(lambda: gate.wait(2.0)))
        t1.start()
        time.sleep(0.05)
        try:
            with pytest.raises(IntegrationUnavailableError):
                client.get("/x")
        finally:
            gate.set()
            t1.join()
