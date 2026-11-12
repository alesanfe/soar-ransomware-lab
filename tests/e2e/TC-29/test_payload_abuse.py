"""TC-29 — chunked transfer + decompression-bomb class payloads.

Boundary coverage the size-limit tests leave: a chunked-encoded request
(no Content-Length) and a gzip payload with a huge expansion ratio. The
contract in both cases: bounded handling — accept-then-validate or clean
4xx, never a memory blow-up or a hang.
"""

from __future__ import annotations

import gzip
import io
import json
import time

import pytest

from tests.e2e.base import E2EBaseTest


@pytest.mark.e2e
class TestPayloadAbuse(E2EBaseTest):
    tc_id = "TC-29"

    def test_chunked_transfer_encoding_bounded(self):
        """Chunked body (no Content-Length) must be handled bounded."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)

        def gen():
            data = json.dumps(payload).encode()
            for i in range(0, len(data), 64):
                yield data[i : i + 64]

        t0 = time.time()
        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            data=gen(),
            headers={
                "Content-Type": "application/json",
                "Transfer-Encoding": "chunked",
            },
            timeout=30,
        )
        elapsed = time.time() - t0
        assert elapsed < 30, f"chunked request took {elapsed:.1f}s"
        assert r.status_code < 500, f"chunked body caused 5xx: {r.status_code}"
        self._log(f"+ chunked body -> HTTP {r.status_code} in {elapsed:.1f}s")

    def test_gzip_bomb_class_body_bounded(self):
        """A small compressed body that expands ~1000x must be bounded:
        either the gateway doesn't decompress (4xx on parse) or it caps the
        expanded size — never an unbounded inflate."""
        big = b'{"alert_id":"' + self.uid("TC29-GZ").encode() + b'","pad":"' + (b"A" * 5_000_000) + b'"}'
        compressed = gzip.compress(big, compresslevel=9)
        ratio = len(big) / max(len(compressed), 1)
        assert ratio > 50, f"fixture not bomb-like: {ratio:.0f}x"
        t0 = time.time()
        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            data=compressed,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
            timeout=30,
        )
        elapsed = time.time() - t0
        assert elapsed < 30, f"gzip-bomb took {elapsed:.1f}s"
        assert r.status_code < 500, (
            f"gzip body caused 5xx: {r.status_code} {r.text[:120]}"
        )
        self._log(
            f"+ gzip {len(compressed)}B -> {len(big)}B ({ratio:.0f}x) "
            f"-> HTTP {r.status_code} in {elapsed:.1f}s"
        )

    def test_nested_zip_like_attachment_bounded(self):
        """A recursive-zip-shaped blob in an evidence field is stored
        verbatim (or rejected) — never recursively inflated server-side."""
        # 42.zip-style: a deflate stream that expands massively
        bomb_bytes = gzip.compress(b"Z" * 2_000_000, compresslevel=9)
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        import base64

        payload["attachment"] = base64.b64encode(bomb_bytes).decode()
        t0 = time.time()
        r = self.shuffle._webhook_session.post(
            self.webhook_url, json=payload, timeout=30,
        )
        elapsed = time.time() - t0
        assert elapsed < 30
        assert r.status_code < 500
