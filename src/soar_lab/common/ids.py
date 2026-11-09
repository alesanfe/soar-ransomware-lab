"""UUIDv7 identifier generation (RFC 9562) with graceful fallback.

Python 3.11's :mod:`uuid` has no ``uuid7`` (it arrives in 3.14), so this
module implements the layout directly: 48-bit Unix-ms timestamp + version
7 + variant + random bits.  Time-sortable identifiers make correlation
keys (``correlation_id``, ``trace_id``, ``alert_id``, ``admission_id``)
lexicographically ordered ≈ chronologically ordered — indexes stay
clustered and artefacts sort meaningfully.

``new_id()`` returns the 32-char hex form used across the codebase
(``uuid.UUID.hex``), keeping W3C trace-context compatibility.
"""

from __future__ import annotations

import secrets
import threading
import time
import uuid

__all__ = ["new_id", "new_uuid7", "uuid7_hex"]

_lock = threading.Lock()
_last_ms = 0
_counter = 0


def uuid7() -> uuid.UUID:
    """Generate an RFC 9562 UUIDv7 (time-ordered, monotonic per process).

    Guarantees strict monotonicity within the process: if two calls land
    in the same millisecond the 12-bit ``rand_a`` field carries a counter
    instead of random bits.  The timestamp+counter pair is produced under
    a lock so concurrent generators cannot collide.
    """
    global _last_ms, _counter
    with _lock:
        ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
        if ms <= _last_ms:
            # Same millisecond (or clock skew): counter keeps order.
            ms = _last_ms
            _counter = (_counter + 1) & 0xFFF
            if _counter == 0:  # counter exhausted — wait out the millisecond
                while ms <= _last_ms:
                    ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
        else:
            _counter = secrets.randbits(12)
        _last_ms = ms
        counter, ts = _counter, ms
    rand_b = secrets.randbits(62)
    value = (ts << 80) | (0x7 << 76) | (counter << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)


def new_uuid7() -> uuid.UUID:
    """Alias kept for call sites that name the version explicitly."""
    return uuid7()


def uuid7_hex() -> str:
    """UUIDv7 as 32-char hex (``uuid.UUID.hex`` form)."""
    return uuid7().hex


def new_id(prefix: str = "") -> str:
    """Time-ordered id with optional ``prefix-`` (e.g. ``alr-``, ``adm-``).

    Uses the full 32-char uuid7 hex: truncating to the first N chars would
    keep only the timestamp bits and lose all randomness (collisions in
    the same millisecond), while truncating the tail loses sortability.
    A constant prefix preserves lexicographic ≈ chronological ordering.
    """
    hex_id = uuid7().hex
    return f"{prefix}-{hex_id}" if prefix else hex_id
