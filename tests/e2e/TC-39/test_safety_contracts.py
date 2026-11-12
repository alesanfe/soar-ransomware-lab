#!/usr/bin/env python3
"""TC-39: safety contracts — clock skew, secret-leak canary, credential
regression, corrupt-backup rejection.

Small, fast checks that pin regressions we already hit for real:
  - detection_time far past/future → bounded webhook response (no 500/hang)
  - a REAL secret must never appear in Loki logs of a workflow run
  - the .env Shuffle key must still authenticate (the drift bug)
  - a corrupted backup is rejected BEFORE any file is touched
"""

import hashlib
import os
import tarfile
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.security,
    pytest.mark.slow,
]


class TestSafetyContracts(E2EBaseTest):
    tc_id = "TC-39"

    def teardown_method(self):
        """Delete TC39-* synthetic metrics docs — skewed detection_time
        values produce insane mttr_seconds whose future @timestamp sorts
        them into the "recent" window sampled by TC-KPI-01."""
        try:
            es_url = self.get_service_url("es")
            self.s.post(
                f"{es_url}/soar-metrics/_delete_by_query?refresh=true",
                json={"query": {"prefix": {"alert_id": "TC39-"}}},
                timeout=30,
            )
        except Exception:
            pass

    # ── TC-39-01: clock skew ──────────────────────────────────────────────

    def test_clock_skew_bounded(self):
        """detection_time ±24h must get a bounded response — accepted and
        normalized, or a clean 4xx; never a 500 or a hang."""
        base = self.build_alert_payload()
        for label, dt in (
            ("future", datetime.now(UTC) + timedelta(hours=24)),
            ("past", datetime.now(UTC) - timedelta(hours=24)),
        ):
            payload = dict(base)
            payload["alert_id"] = f"TC39-SKEW-{label}-{int(time.time())}"
            payload["detection_time"] = dt.isoformat()
            t0 = time.time()
            r = requests.post(self.webhook_url, json=payload, timeout=60)
            elapsed = time.time() - t0
            self._log(f"{label} skew: HTTP {r.status_code} in {elapsed:.1f}s")
            assert elapsed < 60, f"{label} skew hung the webhook"
            assert r.status_code < 500, (
                f"{label} skew caused 5xx: {r.status_code} {r.text[:200]}"
            )

    # ── TC-39-02: secret canary in logs ───────────────────────────────────

    def test_real_secret_never_leaks_to_loki(self):
        """Send an alert, then search Loki for the REAL TheHive API key.
        Zero hits — workflow logs must never contain credentials."""
        secret = self.env.get("THEHIVE_API_KEY", "")
        assert len(secret) >= 16, "no usable THEHIVE_API_KEY for canary check"

        payload = self.build_alert_payload()
        payload["alert_id"] = f"TC39-CANARY-{int(time.time())}"
        payload["detection_time"] = datetime.now(UTC).isoformat()
        self.submit_alert_and_wait(payload, timeout=600)
        time.sleep(15)  # promtail ingest lag

        end = int(time.time() * 1e9)
        start = int((time.time() - 900) * 1e9)
        r = requests.get(
            "https://loki:3100/loki/api/v1/query_range",
            params={
                "query": '{job=~".+"} |= "' + secret + '"',
                "start": start,
                "end": end,
                "limit": 5,
            },
            verify=self._ca_or_false(),
            timeout=20,
        )
        assert r.status_code == 200, f"loki query failed: {r.status_code}"
        results = r.json().get("data", {}).get("result", [])
        leaks = sum(len(s.get("values", [])) for s in results)
        assert leaks == 0, f"THEHIVE_API_KEY found {leaks}× in Loki logs"

    def _ca_or_false(self):
        ca = Path("/app/certs/ca.crt")
        return str(ca) if ca.exists() else False

    # ── TC-39-03: credential sync regression ──────────────────────────────

    def test_shuffle_env_key_still_valid(self):
        """The .env SHUFFLE_DEFAULT_APIKEY must authenticate — the drift bug
        (init-webhook regenerates the key without resyncing env files)
        produced silent 401s twice."""
        key = self.env.get("SHUFFLE_DEFAULT_APIKEY", "")
        assert key, "no SHUFFLE_DEFAULT_APIKEY in env"
        r = requests.get(
            "https://shuffle-backend:5443/api/v1/workflows",
            headers={"Authorization": f"Bearer {key}"},
            timeout=15,
        )
        assert r.status_code == 200, (
            f"env Shuffle key stale: HTTP {r.status_code} — run "
            f"key-resync (init-webhook rotated it without syncing .env*)"
        )

    # ── TC-39-04: corrupt backup rejection ────────────────────────────────

    def test_corrupt_backup_rejected_before_touching_files(self):
        """Flip bytes in a real backup → verify() raises BackupError and
        extract() refuses BEFORE writing anything."""
        from soar_lab.common.exceptions import BackupError
        from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver

        drv = TarBackupDriver()
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src"
            src.mkdir()
            (src / "a.txt").write_text("evidence", encoding="utf-8")
            arc = Path(td) / "b.tar.gz"
            drv.create(str(src), str(arc))
            assert arc.exists() and Path(str(arc) + ".sha256").exists()

            # Corrupt the archive: flip bytes mid-file (breaks gzip + sha).
            data = bytearray(arc.read_bytes())
            mid = len(data) // 2
            data[mid : mid + 8] = b"\xde\xad\xbe\xef\xca\xfe\xba\xbe"
            arc.write_bytes(bytes(data))

            with pytest.raises(BackupError):
                drv.verify(str(arc))

            dest = Path(td) / "dest"
            dest.mkdir()
            sentinel = dest / "keep.txt"
            sentinel.write_text("must survive", encoding="utf-8")
            with pytest.raises(BackupError):
                drv.extract(str(arc), str(dest))
            # Nothing extracted before the integrity gate fired.
            assert sentinel.read_text(encoding="utf-8") == "must survive"
            assert not (dest / "a.txt").exists()

    def test_missing_checksum_sidecar_still_verifies_tar(self):
        """A well-formed tar.gz without .sha256 verifies (sidecar is
        optional); a truncated one does not."""
        from soar_lab.common.exceptions import BackupError
        from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver

        drv = TarBackupDriver()
        with tempfile.TemporaryDirectory() as td:
            arc = Path(td) / "raw.tar.gz"
            payload = Path(td) / "p.txt"
            payload.write_text("x", encoding="utf-8")
            with tarfile.open(arc, "w:gz") as tf:
                tf.add(payload, arcname="p.txt")
            drv.verify(str(arc))  # must not raise

            raw = arc.read_bytes()
            arc.write_bytes(raw[: len(raw) // 2])
            with pytest.raises(BackupError):
                drv.verify(str(arc))
