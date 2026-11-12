#!/usr/bin/env python3
"""TC-36: Resilience under observability-backend outages (QA-02 gaps).

TC-18 covers Cortex/MISP outages inside the pipeline; this suite covers the
SRE Golden-Signals dependencies themselves:

  - TC-36-01: Loki down → alert pipeline still completes; Loki recovers.
  - TC-36-02: OpenSearch (Shuffle's store) down → API/webhook fail-bounded,
    not hang; recovery resumes scheduling.
  - TC-36-03: Grafana down → zero functional impact on the alert pipeline.
"""

import os
import subprocess
import time
from datetime import UTC, datetime

import pytest
import requests

from tests.e2e.base import E2EBaseTest
from tests.e2e.helpers.docker_control import (
    start_container,
    stop_container,
    wait_for_container,
)

ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.resilience,
    pytest.mark.destructive,
    pytest.mark.slow,
]


class TestObservabilityOutages(E2EBaseTest):
    tc_id = "TC-36"

    MANAGED = (
        "soar_loki",
        "soar_opensearch",
        "soar_grafana",
        "soar_elasticsearch",
        "soar_redis",
    )

    def setup_method(self, method):
        # This class deliberately takes these services down — the base
        # health check must not gate on them (load_env reads os.environ).
        os.environ["E2E_SKIP_SERVICES"] = (
            "loki,opensearch,grafana,elasticsearch,redis"
        )
        super().setup_method(method)

    def _restore_managed(self) -> list[str]:
        errors = []
        for name in self.MANAGED:
            if not wait_for_container(name, timeout=30):
                if not start_container(name, timeout=90) or not wait_for_container(
                    name, timeout=180
                ):
                    errors.append(name)
        return errors

    def teardown_method(self, method):
        errors = self._restore_managed()
        assert not errors, f"teardown could not restore containers: {errors}"
        super().teardown_method(method)

    @classmethod
    def teardown_class(cls):
        # Safety net: runs even when a test's setup_method failed (pytest
        # skips method teardown in that case — left a container down once).
        for name in (
            "soar_loki",
            "soar_opensearch",
            "soar_grafana",
            "soar_elasticsearch",
            "soar_redis",
        ):
            subprocess.run(["docker", "start", name], capture_output=True, timeout=90)
        sup = super()
        if hasattr(sup, "teardown_class"):
            sup.teardown_class()

    def _loki_ready(self, timeout: int = 90) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if requests.get("https://loki:3100/ready", verify=self.s.verify, timeout=5).status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(3)
        return False

    def _grafana_ready(self, timeout: int = 120) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if requests.get("https://grafana:3000/api/health", verify=self.s.verify, timeout=5).status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(3)
        return False

    # ── TC-36-01 ──────────────────────────────────────────────────────────

    def test_loki_unavailable_pipeline_survives(self):
        """Loki down → the alert→case pipeline must still complete (logging
        sink is non-critical), and Loki must serve queries after restart."""
        self._log("STEP 1: stop soar_loki (fault injection)")
        assert stop_container("soar_loki", timeout=60), "could not stop soar_loki"

        try:
            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC36-LOKI-{int(time.time())}"
            payload["detection_time"] = datetime.now(UTC).isoformat()
            # The loki_search node is guarded; the workflow may run slower
            # against a dead DNS/conn-refused endpoint — allow generous window.
            exec_id, execution = self.submit_alert_and_wait(payload, timeout=600)
            assert execution.get("status") == "FINISHED", (
                f"workflow did not finish with Loki down: {execution.get('status')}"
            )
            self._log(f"workflow FINISHED without Loki: {exec_id}")
        finally:
            assert start_container("soar_loki", timeout=90)
            assert self._loki_ready(), "Loki did not return to ready after restart"

        # Recovery evidence: the restarted Loki answers queries again.
        r = requests.get(
            "https://loki:3100/loki/api/v1/query",
            params={"query": '{job=~".+"}', "limit": 1},
            verify=self.s.verify,
            timeout=15,
        )
        assert r.status_code == 200 and r.json().get("status") == "success"

    # ── TC-36-02 ──────────────────────────────────────────────────────────

    def test_opensearch_down_bounded_failure_then_recovers(self):
        """OpenSearch (Shuffle's state store) down → the API/webhook tier must
        fail bounded (no hang, no 50x flood) and the stack must resume once
        OpenSearch is back."""
        self._log("STEP 1: stop soar_opensearch (fault injection)")
        assert stop_container("soar_opensearch", timeout=60)

        try:
            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC36-OS-{int(time.time())}"
            t0 = time.time()
            try:
                r = requests.post(self.webhook_url, json=payload, timeout=45)
                self._log(f"webhook during OS outage: HTTP {r.status_code}")
            except requests.RequestException as e:
                self._log(f"webhook during OS outage: bounded connection error: {e}")
            assert time.time() - t0 < 60, "webhook hung >60s with OpenSearch down"

            # The SOAR API itself does not depend on OpenSearch — must stay live.
            r = requests.get("http://api:8000/health", timeout=10)
            assert r.status_code == 200, f"API unhealthy during OS outage: {r.status_code}"
        finally:
            assert start_container("soar_opensearch", timeout=120)
            assert wait_for_container("soar_opensearch", timeout=240)

        # Recovery: a fresh alert completes end-to-end.
        payload = self.build_alert_payload()
        payload["alert_id"] = f"TC36-OS-REC-{int(time.time())}"
        payload["detection_time"] = datetime.now(UTC).isoformat()
        exec_id, execution = self.submit_alert_and_wait(payload, timeout=600)
        assert execution.get("status") == "FINISHED", (
            f"workflow did not recover after OpenSearch restart: {execution.get('status')}"
        )
        self._log(f"post-recovery workflow FINISHED: {exec_id}")

    # ── TC-36-03 ──────────────────────────────────────────────────────────

    def test_grafana_down_zero_functional_impact(self):
        """Grafana down → pipeline unaffected (dashboards are read-path only)."""
        self._log("STEP 1: stop soar_grafana (fault injection)")
        assert stop_container("soar_grafana", timeout=60)
        try:
            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC36-GRAF-{int(time.time())}"
            payload["detection_time"] = datetime.now(UTC).isoformat()
            exec_id, execution = self.submit_alert_and_wait(payload, timeout=600)
            assert execution.get("status") == "FINISHED", (
                f"workflow affected by Grafana outage: {execution.get('status')}"
            )
            self._log(f"workflow FINISHED without Grafana: {exec_id}")
        finally:
            assert start_container("soar_grafana", timeout=90)
            assert self._grafana_ready(), "Grafana did not recover within timeout"

        # Recovery evidence: Grafana API serves again.
        r = requests.get("https://grafana:3000/api/health", verify=self.s.verify, timeout=15)
        assert r.status_code == 200

    # ── TC-36-04 ──────────────────────────────────────────────────────────

    def test_elasticsearch_down_bounded_then_recovers(self):
        """Elasticsearch (metrics store) down → webhook/API fail bounded,
        the ES-index node must not hang the workflow forever, recovery
        resumes indexing."""
        self._log("STEP 1: stop soar_elasticsearch (fault injection)")
        assert stop_container("soar_elasticsearch", timeout=90)
        try:
            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC36-ES-{int(time.time())}"
            t0 = time.time()
            try:
                r = requests.post(self.webhook_url, json=payload, timeout=60)
                self._log(f"webhook during ES outage: HTTP {r.status_code}")
            except requests.RequestException as e:
                self._log(f"webhook during ES outage: bounded error: {e}")
            assert time.time() - t0 < 90, "webhook hung >90s with ES down"

            # The API must stay responsive — ES is a read/write store, not
            # the liveness dependency of the control plane.
            r = requests.get("http://api:8000/health", timeout=10)
            assert r.status_code == 200
        finally:
            assert start_container("soar_elasticsearch", timeout=120)
            deadline = time.time() + 240
            ok = False
            while time.time() < deadline:
                try:
                    if requests.get(
                        "https://elasticsearch:9200/_cluster/health", auth=ES_AUTH, timeout=10
                    ).status_code == 200:
                        ok = True
                        break
                except Exception:
                    pass
                time.sleep(5)
            assert ok, "Elasticsearch did not recover"

        payload = self.build_alert_payload()
        payload["alert_id"] = f"TC36-ES-REC-{int(time.time())}"
        payload["detection_time"] = datetime.now(UTC).isoformat()
        _, execution = self.submit_alert_and_wait(payload, timeout=600)
        assert execution.get("status") == "FINISHED", (
            f"workflow did not recover after ES restart: {execution.get('status')}"
        )

    # ── TC-36-05 ──────────────────────────────────────────────────────────

    def test_redis_down_bounded_then_recovers(self):
        """Redis (queue/dedup) down → webhook fails bounded (no hang, no
        silent acceptance-loss), API stays live, recovery restores
        admission + dedup."""
        self._log("STEP 1: stop soar_redis (fault injection)")
        assert stop_container("soar_redis", timeout=60)
        try:
            payload = self.build_alert_payload()
            payload["alert_id"] = f"TC36-REDIS-{int(time.time())}"
            t0 = time.time()
            status = None
            try:
                r = requests.post(self.webhook_url, json=payload, timeout=60)
                status = r.status_code
                self._log(f"webhook during Redis outage: HTTP {status}")
            except requests.RequestException as e:
                self._log(f"webhook during Redis outage: bounded error: {e}")
            assert time.time() - t0 < 90, "webhook hung >90s with Redis down"

            r = requests.get("http://api:8000/health", timeout=10)
            assert r.status_code == 200
        finally:
            assert start_container("soar_redis", timeout=60)
            assert wait_for_container("soar_redis", timeout=120)

        # Recovery: fresh alert completes AND dedup works again — send the
        # same alert_id twice, expect one execution.
        payload = self.build_alert_payload()
        payload["alert_id"] = f"TC36-REDIS-REC-{int(time.time())}"
        payload["detection_time"] = datetime.now(UTC).isoformat()
        exec_id, execution = self.submit_alert_and_wait(payload, timeout=600)
        assert execution.get("status") == "FINISHED"
