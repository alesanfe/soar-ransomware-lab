# Locust load profile for the SOAR admission path (PERF-001).
#
# Two task mixes:
#   - AdmissionUser: sustained POST /api/v1/alerts (unique idempotency key
#     per request → exercises the real enqueue path, not the dedup cache).
#     Weight 10 — the hot path.
#   - OpsUser: GET /api/v1/queue/metrics + /api/v1/alerts/{id} reads —
#     operational traffic competing with ingest.
#
# Run inside the docker network (api:8000) or against localhost:8000:
#   pip install locust
#   e.g. INTERNAL_SERVICE_TOKEN=... locust -f scripts/perf/locustfile.py
#       --host http://localhost:8000 -u 60 -r 10 -t 5m --headless
#       --json > reports/perf/locust.json
#
# Caution: every admission forwards to Shuffle → each user creates real
# workflow executions. Run when the stack is idle, not during e2e.

"""Locust load profile for the admission endpoint (PERF soak)."""

from __future__ import annotations

import os
import time
import uuid

try:
    from locust import HttpUser, between, task
except ImportError:  # locust not installed — file stays importable for review
    HttpUser = object

    def task(w):  # type: ignore[no-redef]
        return lambda f: f

    def between(a, b):  # type: ignore[no-redef]
        return lambda: a


TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
HEADERS = {"X-Service-Token": TOKEN}


def _payload(tag: str) -> dict:
    rid = uuid.uuid4().hex[:12]
    return {
        "alert_id": f"locust-{tag}-{rid}",
        "alert_type": "ransomware",
        "event_type": "ransomware_detection",
        "hostname": f"locust-host-{rid[:6]}",
        "src_ip": f"192.168.77.{int(rid[:2], 16) % 250 + 1}",
        "hash": uuid.uuid4().hex + uuid.uuid4().hex[:32],
        "severity": 2,
        "source": "locust-load",
        "description": "Locust sustained-load probe — synthetic, harmless",
        "idempotency_key": f"locust-{tag}-{rid}",
        "timestamp": time.time(),
    }


class AdmissionUser(HttpUser):
    """Sustained admission traffic — the PERF-001 hot path."""

    weight = 10
    wait_time = between(0.05, 0.2)

    @task
    def admit(self) -> None:
        with self.client.post(
            "/api/v1/alerts",
            json=_payload("a"),
            headers=HEADERS,
            name="POST /api/v1/alerts",
            catch_response=True,
        ) as resp:
            if resp.status_code == 202:
                resp.success()
            elif resp.status_code in (429, 503):
                # Controlled rejection is CORRECT behaviour under
                # saturation: 503 = queue backpressure, 429 = rate-limit
                # bucket (service tokens get a per-token bucket too —
                # middleware/rate_limit.py). Both protect the pipeline.
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}: {resp.text[:120]}")


class OpsUser(HttpUser):
    """Operational reads competing with ingest (queue metrics, status)."""

    weight = 2
    wait_time = between(0.5, 2.0)

    @task(3)
    def queue_metrics(self) -> None:
        with self.client.get(
            "/api/v1/queue/metrics",
            headers=HEADERS,
            name="GET /queue/metrics",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 429, 503):
                # 429/503 = controlled rejection — same contract as POSTs.
                resp.success()

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")
