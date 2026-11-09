"""R3: WorkerLease — single leader for singleton worker duties."""

import pytest

from soar_lab.infrastructure.messaging.worker_lease import (
    LEASE_KEY,
    WorkerLease,
)


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, **_kwargs):
        self.data[key] = value

    async def delete(self, key):
        self.data.pop(key, None)


class TestLease:
    @pytest.mark.asyncio
    async def test_first_holder_acquires(self):
        r = FakeRedis()
        lease = WorkerLease(r, "w1")
        assert await lease.held() is True
        assert r.data[LEASE_KEY] == "w1"

    @pytest.mark.asyncio
    async def test_second_worker_denied(self):
        r = FakeRedis()
        assert await WorkerLease(r, "w1").held() is True
        assert await WorkerLease(r, "w2").held() is False

    @pytest.mark.asyncio
    async def test_takeover_after_release(self):
        r = FakeRedis()
        l1 = WorkerLease(r, "w1")
        assert await l1.held() is True
        await l1.release()
        assert await WorkerLease(r, "w2").held() is True

    @pytest.mark.asyncio
    async def test_release_only_own_lease(self):
        r = FakeRedis()
        l1 = WorkerLease(r, "w1")
        await l1.held()
        await WorkerLease(r, "w2").release()  # w2 doesn't hold it
        assert r.data[LEASE_KEY] == "w1"

    @pytest.mark.asyncio
    async def test_no_client_degrades_to_leader(self):
        # Standalone/single-worker deployment — no lock service needed.
        assert await WorkerLease(None, "w1").held() is True
