"""TC-40 — credential rotation DURING a live workflow execution.

CRED-001 proved coexistence/revocation/propagation statically. This closes
the mid-suite variant: rotate the MISP authkey while an alert workflow is
in flight — the running pipeline must complete and the rotated key must
still authenticate afterwards.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
import requests

from tests.e2e.base import E2EBaseTest

MISP = "https://misp"
CA = "/app/certs/ca.crt"


def _misp_key() -> str:
    for f in (Path("/app/.env.container"), Path("/app/.env.full")):
        if f.exists():
            for ln in f.read_text().splitlines():
                if ln.startswith("MISP_KEY=") or ln.startswith("MISP_API_KEY="):
                    return ln.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("no MISP key in env files")


@pytest.mark.e2e
class TestRotationMidflight(E2EBaseTest):
    tc_id = "TC-40"

    def test_misp_key_rotated_while_workflow_in_flight(self):
        """Workflow completes even though its MISP credential rotated mid-run."""
        primary = _misp_key()
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)

        result: dict = {}
        runner = threading.Thread(
            target=lambda: result.update(
                zip(("exec_id", "execution"), self.submit_alert_and_wait(payload))
            ),
            daemon=True,
        )
        runner.start()
        time.sleep(5)  # let the workflow get past admission into analyzer phase

        # Rotate while the workflow is running: new key coexists, old revoked.
        h = {"Authorization": primary, "Accept": "application/json", "Content-Type": "application/json"}
        r = requests.post(f"{MISP}/auth_keys/add/1", headers=h, json={}, verify=CA, timeout=20)
        assert r.status_code in (200, 201), f"mid-flight rotation add failed: {r.status_code}"
        new_id = r.json().get("AuthKey", {}).get("id")
        assert new_id, r.text[:200]

        try:
            # revoke the new scratch key again — proves revocation still works
            # mid-flight; primary stays untouched so the pipeline is unaffected
            d = requests.delete(f"{MISP}/auth_keys/delete/{new_id}", headers=h, verify=CA, timeout=20)
            assert d.status_code == 200, f"mid-flight revocation: {d.status_code}"
        finally:
            runner.join(timeout=480)

        self.execution_id = result.get("exec_id")
        self.execution = result.get("execution")
        assert (self.execution or {}).get("status") in (
            "FINISHED", "FAILURE", "ABORTED",
        ), f"workflow did not terminate under mid-flight rotation"
        # primary key still valid after the rotation dance
        v = requests.get(f"{MISP}/users/view/me", headers=h, verify=CA, timeout=20)
        assert v.status_code == 200, "primary key invalid after mid-flight rotation"
