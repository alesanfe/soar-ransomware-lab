"""R3: WorkerLease — single leader for singleton worker duties."""

import asyncio

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

    async def set(self, key, value, nx=False, **_kwargs):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True

    async def delete(self, key):
        self.data.pop(key, None)

    async def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    async def eval(self, script, numkeys, key, holder, *_args):
        # In-order emulation of the atomic Lua lease scripts.
        if "DEL" in script:
            if self.data.get(key) == holder:
                self.data.pop(key, None)
                return 1
            return 0
        current = self.data.get(key)
        if current == holder:
            return 1
        if current is None:
            self.data[key] = holder
            return 2
        return 0


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

    async def test_concurrent_acquire_single_winner(self):
        # WORKER-006: N workers arriving at an empty lease key must
        # produce exactly one leader — the old GET+SET let both read
        # None and both SET, double-leading for a cycle.
        r = FakeRedis()
        results = await asyncio.gather(
            *(WorkerLease(r, f"w{i}").held() for i in range(8))
        )
        assert sorted(results) == [False] * 7 + [True]

    async def test_renew_same_epoch_no_fence_bump(self):
        r = FakeRedis()
        lease = WorkerLease(r, "w1")
        await lease.held()
        first = lease.fence_token
        await lease.held()  # renew, not re-acquire
        assert lease.fence_token == first

    async def test_reacquire_after_expiry_new_epoch(self):
        r = FakeRedis()
        l1 = WorkerLease(r, "w1")
        await l1.held()
        await l1.release()
        l2 = WorkerLease(r, "w2")
        await l2.held()
        assert l2.fence_token == (l1.fence_token or 0) + 1
