#!/usr/bin/env python3
"""
TC-35: Grafana dashboards — render + data contract end-to-end.

Regression suite for the observability stack (GRAF-007): every
provisioned dashboard panel must render a real PNG through the
grafana-image-renderer sidecar, datasource queries must return
non-degenerate data (the piecharts-collapsed-to-one-slice class of bug
is caught by asserting bucket counts, not HTTP 200), the alert
notification pipeline (Grafana -> SOAR API webhook -> Loki) is exercised
end-to-end, and Prometheus scrape targets are verified up.
"""

import time

import requests

from tests.e2e.base import E2EBaseTest

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Tempo trace-search panels over wide windows take ~65s to render; the
# test shrinks the window to 1h and keeps headroom for the image-renderer.
RENDER_TIMEOUT_S = 120
MIN_PNG_BYTES = 2_000  # a degenerate/blank render is far smaller than a real panel

EXPECTED_DASHBOARDS = {"soar-kpi-main", "soar-logs", "soar-traces", "soar-saturation"}
EXPECTED_DATASOURCES = {"elasticsearch", "loki", "tempo", "prometheus", "soar-api"}


class TestGrafanaRendering(E2EBaseTest):
    """Dashboards render real data and the alert pipeline is closed-loop."""

    tc_id = "TC-35"

    def setup_method(self, method):
        super().setup_method(method)
        self.grafana = self.get_service_url("grafana").rstrip("/")
        self.api = self.get_service_url("api").rstrip("/")
        self.gs = requests.Session()
        self.gs.verify = False
        user = self.env.get("GRAFANA_ADMIN_USER", "admin")
        password = self.env.get("GRAFANA_ADMIN_PASSWORD", "")
        self.gs.auth = (user, password)

    # ---------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------
    def _dashboard(self, uid: str) -> dict:
        r = self.gs.get(f"{self.grafana}/api/dashboards/uid/{uid}", timeout=15)
        r.raise_for_status()
        return r.json()["dashboard"]

    @staticmethod
    def _panel_ids(dashboard: dict) -> list[int]:
        """Flatten panels incl. nested rows; skip non-renderable types."""
        ids = []

        def walk(panels):
            for p in panels:
                if p.get("type") == "row":
                    walk(p.get("panels", []))
                elif "id" in p:
                    ids.append(p["id"])

        walk(dashboard.get("panels", []))
        return ids

    def _render(self, uid: str, panel_id: int, var_query: str = "") -> bytes:
        url = (
            f"{self.grafana}/render/d-solo/{uid}"
            f"?panelId={panel_id}&width=800&height=400&tz=UTC"
            f"&from=now-1h&to=now{var_query}"
        )
        r = None
        for attempt in range(2):
            try:
                r = self.gs.get(url, timeout=RENDER_TIMEOUT_S)
                break
            except requests.exceptions.ReadTimeout:
                if attempt == 1:
                    raise
                time.sleep(10)  # renderer+tempo search can be marginal; retry once
        assert (
            r.status_code == 200
        ), f"render uid={uid} panel={panel_id} -> HTTP {r.status_code}: {r.text[:200]}"
        return r.content

    # ---------------------------------------------------------------
    # provisioning / health
    # ---------------------------------------------------------------
    def test_grafana_health_database_ok(self):
        r = self.gs.get(f"{self.grafana}/api/health", timeout=10)
        assert r.status_code == 200, f"grafana /api/health -> {r.status_code}"
        body = r.json()
        assert body.get("database") == "ok", f"grafana database not ok: {body}"

    def test_all_dashboards_provisioned(self):
        r = self.gs.get(f"{self.grafana}/api/search?type=dash-db", timeout=15)
        r.raise_for_status()
        uids = {d["uid"] for d in r.json()}
        missing = EXPECTED_DASHBOARDS - uids
        assert not missing, f"dashboards missing: {missing} (found: {sorted(uids)})"

    def test_all_datasources_resolve(self):
        r = self.gs.get(f"{self.grafana}/api/datasources", timeout=15)
        r.raise_for_status()
        uids = {d["uid"] for d in r.json()}
        missing = EXPECTED_DATASOURCES - uids
        assert not missing, f"datasources missing: {missing} (found: {sorted(uids)})"

    # ---------------------------------------------------------------
    # render contract — every panel of every dashboard
    # ---------------------------------------------------------------
    def test_every_panel_renders_real_png(self):
        failures = []
        for uid in sorted(EXPECTED_DASHBOARDS):
            try:
                dash = self._dashboard(uid)
            except Exception as exc:
                failures.append(f"{uid}: cannot load dashboard: {exc}")
                continue
            var_query = "&var-DS_ELASTICSEARCH=elasticsearch"
            for pid in self._panel_ids(dash):
                try:
                    png = self._render(uid, pid, var_query)
                    assert png[:8] == PNG_MAGIC, "not a PNG"
                    assert len(png) > MIN_PNG_BYTES, f"PNG too small ({len(png)}B)"
                except AssertionError as exc:
                    failures.append(f"{uid}/panel{pid}: {exc}")
                except Exception as exc:
                    failures.append(f"{uid}/panel{pid}: {type(exc).__name__}: {exc}")
        assert not failures, "render failures:\n" + "\n".join(failures)

    # ---------------------------------------------------------------
    # non-degeneracy — the piecharts-collapsed-to-"Count" regression
    # ---------------------------------------------------------------
    def test_es_terms_agg_returns_multiple_buckets(self):
        body = {
            "queries": [
                {
                    "refId": "A",
                    "datasource": {"type": "elasticsearch", "uid": "elasticsearch"},
                    "metrics": [{"id": "1", "type": "count"}],
                    "bucketAggs": [
                        {
                            "id": "2",
                            "type": "terms",
                            "field": "alert_type",
                            "settings": {"size": "10", "order": "desc", "orderBy": "_count"},
                        }
                    ],
                    "timeField": "@timestamp",
                }
            ],
            "from": str(int(time.time() * 1000) - 7 * 24 * 3600 * 1000),
            "to": str(int(time.time() * 1000)),
        }
        r = self.gs.post(f"{self.grafana}/api/ds/query", json=body, timeout=30)
        assert r.status_code == 200, f"ds/query -> {r.status_code}: {r.text[:300]}"
        frames = r.json()["results"]["A"]["frames"]
        assert frames, "terms agg returned no frames"
        rows = frames[0]["data"]["values"][0]
        assert len(rows) > 1, (
            f"alert_type terms agg degenerated to {len(rows)} bucket(s) — "
            "piechart would render a single 'Count' slice"
        )

    def test_loki_recent_logs_nonzero(self):
        body = {
            "queries": [
                {
                    "refId": "A",
                    "datasource": {"type": "loki", "uid": "loki"},
                    "expr": 'sum(count_over_time({compose_project=~".+"}[5m]))',
                    "queryType": "instant",
                }
            ],
            "from": str(int(time.time() * 1000) - 900 * 1000),
            "to": str(int(time.time() * 1000)),
        }
        r = self.gs.post(f"{self.grafana}/api/ds/query", json=body, timeout=30)
        assert r.status_code == 200, f"loki ds/query -> {r.status_code}: {r.text[:300]}"
        frames = r.json()["results"]["A"]["frames"]
        assert frames, "loki instant query returned no frames"
        values = frames[0]["data"]["values"][-1]
        assert values and values[-1] > 0, "no log lines in the last 5m — promtail pipeline dead?"

    # ---------------------------------------------------------------
    # alert notification pipeline (GRAF-ALERT-RX)
    # ---------------------------------------------------------------
    def test_contact_point_provisioned(self):
        r = self.gs.get(f"{self.grafana}/api/v1/provisioning/contact-points", timeout=15)
        r.raise_for_status()
        names = {cp.get("name") for cp in r.json()}
        assert "soar-api-webhook" in names, f"contact point missing (found: {sorted(names)})"

    def test_notification_policy_routes_to_webhook(self):
        r = self.gs.get(f"{self.grafana}/api/v1/provisioning/policies", timeout=15)
        r.raise_for_status()
        tree = r.json()
        assert (
            tree.get("receiver") == "soar-api-webhook"
        ), f"root policy receiver is {tree.get('receiver')!r}, expected soar-api-webhook"

    def test_grafana_alert_webhook_accepts_notification(self):
        payload = {
            "status": "firing",
            "receiver": "soar-api-webhook",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "TC35SyntheticProbe", "severity": "info"},
                    "annotations": {"summary": "TC-35 delivery probe"},
                    "startsAt": "2024-01-01T00:00:00Z",
                    "fingerprint": f"tc35-{int(time.time())}",
                }
            ],
        }
        # self.s carries X-Service-Token from E2EBaseTest.setup_method.
        r = self.s.post(f"{self.api}/api/v1/alerts/grafana", json=payload, timeout=15)
        assert r.status_code == 200, f"webhook -> {r.status_code}: {r.text[:200]}"
        assert r.json().get("received") == 1

        # counter must be exposed at /metrics
        m = self.s.get(f"{self.api}/metrics", timeout=10)
        assert (
            "soar_grafana_alert_notifications_total" in m.text
        ), "grafana alert counter missing from /metrics"

    def test_delivered_alert_visible_in_loki(self):
        """Closed loop: the webhook log line must be queryable in Loki."""
        loki = self.get_service_url("loki").rstrip("/")
        marker = "TC35SyntheticProbe"
        # send the probe first
        self.s.post(
            f"{self.api}/api/v1/alerts/grafana",
            json={
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": marker, "severity": "info"},
                        "annotations": {"summary": "TC-35 loki visibility probe"},
                    }
                ],
            },
            timeout=15,
        )
        deadline = time.time() + 90  # promtail scrape + loki ingest lag
        hits = 0
        while time.time() < deadline:
            r = self.s.get(
                f"{loki}/loki/api/v1/query_range",
                params={
                    "query": f'{{compose_service="api"}} |= "{marker}"',
                    "start": int((time.time() - 300) * 1e9),
                    "end": int(time.time() * 1e9),
                    "limit": 5,
                },
                timeout=15,
            )
            if r.status_code == 200:
                hits = len(r.json().get("data", {}).get("result", []))
                if hits:
                    break
            time.sleep(5)
        assert hits > 0, "grafana_alert log line never reached Loki (pipeline broken)"

    # ---------------------------------------------------------------
    # saturation coverage (GRAF-OBS-02)
    # ---------------------------------------------------------------
    def test_prometheus_targets_up(self):
        r = self.s.get("http://prometheus:9090/api/v1/targets?state=active", timeout=15)
        assert r.status_code == 200, f"prometheus /targets -> {r.status_code}"
        targets = r.json()["data"]["activeTargets"]
        health = {t["labels"]["job"]: t["health"] for t in targets}
        assert "soar-api" in health, f"soar-api job missing (jobs: {sorted(health)})"
        down = {j: h for j, h in health.items() if h != "up"}
        assert not down, f"prometheus targets down: {down}"
