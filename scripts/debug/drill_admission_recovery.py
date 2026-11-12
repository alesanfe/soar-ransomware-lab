"""Live admission-pipeline recovery drill against the real Redis Streams backend.

Exercises the real ``RedisStreamsQueue`` code path on a scratch stream
(``soar:drill:*``) without touching the production ``soar:admissions`` stream:

1. Crash recovery — entry read but never acked is reclaimed via XAUTOCLAIM.
2. DLQ lifecycle — dead-letter → list → redrive → re-delivered.

Run inside ``soar_api``: ``python /app/scripts/debug/drill_admission_recovery.py``
"""

import asyncio
import os

import redis.asyncio as aioredis

from soar_lab.infrastructure.messaging.redis_streams_queue import RedisStreamsQueue

GROUP = "drill-g"


async def main() -> None:
    client = aioredis.from_url(os.environ["REDIS_URL"])
    stream, dlq = "soar:drill:admissions", "soar:drill:admissions:dlq"
    await client.delete(stream, dlq)
    q = RedisStreamsQueue(client, stream=stream, dlq_stream=dlq)

    # 1) Crash recovery: "crasher" reads but dies before ack → pending entry.
    await q.enqueue({"admission_id": "drill-1", "event_id": "e1"})
    batch = await q.read(GROUP, "crasher", count=1, block_ms=100)
    assert batch, "entry not delivered"
    metrics = await q.metrics(GROUP)
    print("pending after crash:", metrics)
    assert metrics["pending"] == 1

    # Surviving consumer reclaims the stale entry (min_idle=0 forces claim).
    claimed = await q.claim_stale(GROUP, "survivor", min_idle_ms=0)
    assert claimed and claimed[0][1]["admission_id"] == "drill-1", f"claim: {claimed}"
    await q.ack(GROUP, claimed[0][0])
    assert (await q.metrics(GROUP))["pending"] == 0, "still pending after ack"
    print("RECOVERY OK: stale pending entry claimed + acked")

    # 2) DLQ lifecycle: dead-letter → list → redrive → re-delivery.
    await q.enqueue({"admission_id": "drill-2"})
    b2 = await q.read(GROUP, "c2", count=1, block_ms=100)
    await q.dead_letter(b2[0][1], reason="drill_terminal")
    await q.ack(GROUP, b2[0][0])
    dl = await q.dlq_list()
    assert dl and dl[0]["reason"] == "drill_terminal", f"dlq shape: {dl}"
    assert dl[0]["payload"]["admission_id"] == "drill-2"
    print("dlq entry:", dl[0]["dlq_entry_id"])
    ok = await q.dlq_redrive(dl[0]["dlq_entry_id"], group=GROUP)
    assert ok, "redrive returned False"
    b3 = await q.read(GROUP, "c3", count=1, block_ms=100)
    assert b3 and b3[0][1]["admission_id"] == "drill-2", "redriven entry not re-delivered"
    await q.ack(GROUP, b3[0][0])
    assert await q.dlq_size() == 0
    print("DLQ OK: dead-letter -> list -> redrive -> redelivered")

    await client.delete(stream, dlq)
    await client.aclose()
    print("DRILL PASSED")


if __name__ == "__main__":
    asyncio.run(main())
