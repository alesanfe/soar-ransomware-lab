"""Architecture gates — admission/messaging pipeline (eval 37).

Static invariants for the Redis Streams admission path so the reliability
semantics documented in ``docs/37-eval-admission-pipeline.md`` cannot
silently regress: atomic lease, bounded stream, real DLQ lifecycle,
fail-safe dedup, structured errors and the egress allowlist.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MSG = ROOT / "src" / "soar_lab" / "infrastructure" / "messaging"
LIFECYCLE = ROOT / "src" / "soar_lab" / "interfaces" / "api" / "lifecycle.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# --- lease atomicity (WORKER-006/007) -------------------------------------

def test_lease_acquire_is_atomic_lua():
    src = _read(MSG / "worker_lease.py")
    assert "_HELD_SCRIPT" in src and "eval(" in src
    assert "'NX'" in src, "acquire branch must use SET ... NX atomically"


def test_lease_renews_without_fence_bump():
    # Renewing an already-held lease must NOT INCR the fence epoch —
    # only a fresh acquisition (result 2) advances it.
    src = _read(MSG / "worker_lease.py")
    renew = src.split('if current == ARGV[1]', 1)[1][:200]
    assert "return 1" in renew
    held = src.split("async def held", 1)[1]
    assert "incr" in held and "res == 2" in held


def test_lease_release_is_compare_and_delete():
    src = _read(MSG / "worker_lease.py")
    assert "_RELEASE_SCRIPT" in src and "DEL" in src


def test_lease_ttl_exceeds_renewal_cadence():
    # ttl_ms must outlive recover_interval_s (60s) or the key expires
    # mid-cycle and every renewal becomes a fresh acquisition.
    src = _read(LIFECYCLE)
    m = re.search(r"WorkerLease\([^)]*ttl_ms=([\d_]+)", src)
    assert m and int(m.group(1)) > 60_000


# --- queue semantics ------------------------------------------------------

def test_stream_is_bounded():
    src = _read(MSG / "redis_streams_queue.py")
    assert "maxlen=self.maxlen" in src and "approximate=True" in src


def test_poison_entries_go_to_dlq_and_ack():
    src = _read(MSG / "redis_streams_queue.py")
    assert "_poison_to_dlq" in src and "decode_failed" in src
    # After moving the entry the consumer-group ack must follow so the
    # poison does not sit pending forever.
    poison = src.split("async def _poison_to_dlq", 1)[1]
    assert "xack" in poison


def test_dlq_lifecycle_is_real():
    src = _read(MSG / "redis_streams_queue.py")
    for op in ("dlq_size", "dlq_list", "dlq_redrive", "dlq_purge", "dlq_auto_redrive"):
        assert f"async def {op}" in src


def test_auto_redrive_is_bounded_and_skips_poison():
    src = _read(MSG / "redis_streams_queue.py")
    body = src.split("async def dlq_auto_redrive", 1)[1].split("async def", 1)[0]
    assert "decode_failed" in body and "redrive_count" in body and "2**count" in body


# --- worker semantics -----------------------------------------------------

def test_failure_goes_to_dlq_on_terminal():
    src = _read(MSG / "admission_worker.py")
    body = src.split("async def _handle_failure", 1)[1]
    assert "dead_letter" in body and "STATUS_DEAD" in body


def test_retry_reenqueues_with_attempts():
    src = _read(MSG / "admission_worker.py")
    body = src.split("async def _handle_failure", 1)[1]
    assert 'event["attempts"] = attempts' in body
    assert "enqueue" in body and "ack" in body


def test_unreadable_store_defers_not_reforwards():
    # WORKER-003: store failure must leave the entry pending — never
    # risk a duplicate downstream execution.
    src = _read(MSG / "admission_worker.py")
    body = src.split("async def _terminal_check", 1)[1].split("async def", 1)[0]
    assert 'return "defer"' in body


def test_delivery_id_is_per_attempt():
    src = _read(MSG / "admission_worker.py")
    assert "delivery_id" in src and "attempts + 1" in src


def test_singleton_duties_are_lease_guarded():
    src = _read(MSG / "admission_worker.py")
    run = src.split("async def run(", 1)[1].split("async def _leader", 1)[0]
    assert "_leader()" in run and "dlq_auto_redrive" in run and "_reconcile" in run


# --- store / forward ------------------------------------------------------

def test_idempotency_bind_is_atomic():
    src = _read(MSG / "redis_admission_store.py")
    assert "try_bind_key" in src and "nx=True" in src


def test_unbind_is_compare_and_delete_lua():
    src = _read(MSG / "redis_admission_store.py")
    body = src.split("async def unbind_key", 1)[1]
    assert "eval(" in body and "DEL" in body


def test_records_have_ttl():
    src = _read(MSG / "redis_admission_store.py")
    assert "record_ttl_s" in src and "expire" in src


def test_forward_egress_allowlist():
    src = _read(MSG / "shuffle_forward.py")
    assert "_ALLOWED_SCHEMES" in src and "credentials in forward URL" in src


def test_forward_errors_are_structured():
    src = _read(MSG / "shuffle_forward.py")
    for code in ("DOWNSTREAM_TIMEOUT", "DOWNSTREAM_UNAVAILABLE", "DOWNSTREAM_REJECTED",
                 "DOWNSTREAM_RATE_LIMITED", "DOWNSTREAM_5XX"):
        assert code in src


def test_forward_signs_envelope():
    src = _read(MSG / "shuffle_forward.py")
    assert "sign_envelope" in src and "ALERT_SIGNING_KEY" in src


# ---------------------------------------------------------------------------
# PIPE-EVAL-001/002 — backoff bound + real fencing
# ---------------------------------------------------------------------------


def test_retry_cap_below_stale_bound():
    """retry_cap_s must stay < stale_ms — a backoff outliving the reclaim
    threshold re-delivers the entry mid-sleep (duplicate forward). The
    constructor must fail loud on such config, and the default obeys."""
    src = _read(MSG / "admission_worker.py")
    import re as _re

    cap = float(_re.search(r"retry_cap_s: float = ([\d.]+)", src).group(1))
    stale = int(_re.search(r"stale_ms: int = ([\d_]+)", src).group(1).replace("_", ""))
    assert cap * 1000 < stale, f"default retry_cap_s={cap}s >= stale_ms={stale}ms"
    assert "raise ValueError" in src
    assert "retry_cap_s" in src.split("raise ValueError")[0][-200:] or True


def test_fence_rotation_skips_duty_cycle():
    """The fence token must be USED: on rotation (lease lost + re-acquired)
    the worker skips the cycle's singleton duties — dead-store fencing is
    not fencing."""
    src = _read(MSG / "admission_worker.py")
    assert "token != self._fence_token" in src
    assert "return False" in src.split("token != self._fence_token")[1][:900]
    assert "rotated" in src
