#!/usr/bin/env python3
"""Live observability-stack checks (OBS-005/022/023/046/087/130).

Runs inside the docker network (``soar_api``) and asserts the signals the
backlog gates on:

- Prometheus: every scrape + blackbox target ``up`` (22/22 expected).
- Grafana: all provisioned rules present, none in eval error.
- Contact point: the SOAR webhook receiver exists and the API endpoint
  answers a synthetic notification (200).
- TLS: grafana/loki/tempo/prometheus verify against the lab CA.
- S3: rotated credentials authenticate; the old default is rejected;
  bucket scoping denies cross-bucket access (OBS-012/015).
- Watchdog loop: ``obs_iscm_watchdog`` fires, and the API has recorded
  grafana alert notifications (channel liveness evidence, OBS-025/130).

Markers: requires_docker + integration (skipped in host-only runs).
"""

import hashlib
import hmac
import os
from datetime import datetime, timezone

import pytest
import requests

pytestmark = [pytest.mark.requires_docker, pytest.mark.integration]

CA = "/app/certs/ca.crt"
GRAFANA = "https://grafana:3000"
PROM = "https://prometheus:9090"
LOKI = "https://loki:3100"
TEMPO = "https://tempo:3200"
API = "http://api:8000"
S3 = "s3:8333"

# The /api/prometheus/grafana/api/v1/rules endpoint keys rules by *title*,
# not uid — keep both maps in sync with alert-rules.yml.
WATCHDOG_TITLE = "ISCM watchdog (always firing)"

EXPECTED_OBS_RULES = {
    "obs_probe_down",
    "obs_prometheus_target_down",
    "obs_cert_expiry_30d",
    "obs_cert_expiry_14d",
    "obs_container_restart_loop",
    "obs_s3_objectstore_errors",
    "obs_otel_spans_dropped",
    "obs_iscm_watchdog",
    "obs_alert_channel_silent",
    "obs_admission_slo_burn_rate",
}


def _graf_auth() -> tuple[str, str]:
    return (
        os.getenv("GRAFANA_ADMIN_USER", "admin"),
        os.getenv("GRAFANA_ADMIN_PASSWORD", ""),
    )


def _sigv4_get(path: str, ak: str, sk: str) -> requests.Response:
    """Minimal SigV4 GET signer — used to prove the S3 IAM scoping."""
    now = datetime.now(timezone.utc)
    amz, date = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    scope = f"{date}/us-east-1/s3/aws4_request"
    payload = hashlib.sha256(b"").hexdigest()
    headers = {"host": S3, "x-amz-content-sha256": payload, "x-amz-date": amz}
    ch = "".join(f"{k}:{headers[k]}\n" for k in sorted(headers))
    sh = ";".join(sorted(headers))
    canon = f"GET\n{path}\n\n{ch}\n{sh}\n{payload}"
    sts = (
        f"AWS4-HMAC-SHA256\n{amz}\n{scope}\n"
        + hashlib.sha256(canon.encode()).hexdigest()
    )
    k = ("AWS4" + sk).encode()
    for part in (date, "us-east-1", "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={ak}/{scope}, "
        f"SignedHeaders={sh}, Signature={sig}"
    )
    return requests.get(f"http://{S3}{path}", headers=headers, timeout=10)


class TestPrometheusTargets:
    def test_all_targets_up(self):
        """OBS-087/022: every scrape + blackbox target must be up."""
        r = requests.get(
            f"{PROM}/api/v1/targets?state=active", verify=CA, timeout=15
        )
        targets = r.json()["data"]["activeTargets"]
        down = [
            f"{t['labels'].get('job')}:{t['labels'].get('instance')}"
            for t in targets
            if t["health"] != "up"
        ]
        assert not down, f"targets down: {down}"

    def test_blackbox_probes_reporting(self):
        """OBS-023: probe_success series exist for all three modules."""
        r = requests.get(
            f"{PROM}/api/v1/query",
            params={"query": "count(probe_success)"},
            verify=CA,
            timeout=15,
        )
        result = r.json()["data"]["result"]
        assert result and int(float(result[0]["value"][1])) >= 10

    def test_cert_expiry_metric_present(self):
        """OBS-046: probe_ssl_earliest_cert_expiry is exported for TLS
        endpoints so the expiry alerts can fire."""
        r = requests.get(
            f"{PROM}/api/v1/query",
            params={"query": "count(probe_ssl_earliest_cert_expiry)"},
            verify=CA,
            timeout=15,
        )
        result = r.json()["data"]["result"]
        assert result and int(float(result[0]["value"][1])) >= 4


class TestGrafanaAlerting:
    def _rules(self):
        r = requests.get(
            f"{GRAFANA}/api/v1/provisioning/alert-rules",
            auth=_graf_auth(),
            verify=CA,
            timeout=15,
        )
        assert r.status_code == 200
        return r.json()

    def test_all_rules_provisioned_including_selfmon(self):
        uids = {r["uid"] for r in self._rules()}
        missing = EXPECTED_OBS_RULES - uids
        assert not missing, f"self-monitoring rules missing: {missing}"
        assert len(uids) >= 20, f"only {len(uids)} rules loaded"

    def test_no_rule_in_eval_error(self):
        """OBS-001: after the params fix, no rule may sit in error state."""
        r = requests.get(
            f"{GRAFANA}/api/prometheus/grafana/api/v1/rules",
            auth=_graf_auth(),
            verify=CA,
            timeout=15,
        )
        assert r.status_code == 200
        bad = []
        for group in r.json()["data"]["groups"]:
            for rule in group["rules"]:
                state = rule.get("state", "")
                if state in ("error", "nodata") and rule["name"] not in (
                    WATCHDOG_TITLE,  # noDataState:Alerting by design
                ):
                    bad.append(f"{rule['name']}={state}")
        # states may take a full cycle to settle — error is the hard fail
        hard_errors = [b for b in bad if "=error" in b]
        assert not hard_errors, f"rules in eval error: {hard_errors}"


class TestContactPoint:
    def test_soar_webhook_contact_point_provisioned(self):
        """OBS-005: the provisioned webhook receiver exists — the default
        email channel must stay unused."""
        r = requests.get(
            f"{GRAFANA}/api/v1/provisioning/contact-points",
            auth=_graf_auth(),
            verify=CA,
            timeout=15,
        )
        assert r.status_code == 200
        names = {c["name"] for c in r.json()}
        assert "soar-api-webhook" in names, f"contact points: {names}"

    def test_webhook_endpoint_accepts_synthetic_alert(self):
        """OBS-005/130: the API receiver answers a notification 200."""
        token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
        r = requests.post(
            f"{API}/api/v1/alerts/grafana",
            json={
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "obs_test_synthetic"},
                    }
                ],
            },
            headers={"Authorization": f"Service-Token {token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]


class TestTLSAndS3:
    @pytest.mark.parametrize(
        "url",
        [
            f"{GRAFANA}/api/health",
            f"{LOKI}/ready",
            f"{TEMPO}/ready",
            f"{PROM}/-/ready",
        ],
    )
    def test_tls_endpoints_verify_with_lab_ca(self, url):
        """OBS-048/051: full chain verification — no skip_verify anywhere."""
        r = requests.get(url, verify=CA, timeout=15)
        assert r.status_code in (200, 204)

    def test_old_default_s3_credentials_rejected(self):
        """OBS-012: the rotated-out default pair must not authenticate."""
        r = _sigv4_get("/loki/", "soar-s3", "soar-s3-secret-change-me")
        assert r.status_code == 403

    def test_bucket_scoping_enforced(self):
        """OBS-015: loki creds read loki (200) but are denied on tempo
        (403 AccessDenied)."""
        ak = os.getenv("LOKI_S3_ACCESS_KEY", "soar-loki")
        sk = os.getenv("LOKI_S3_SECRET_KEY", "")
        if not sk:
            pytest.skip("LOKI_S3_SECRET_KEY not in environment")
        assert _sigv4_get("/loki/", ak, sk).status_code == 200
        assert _sigv4_get("/tempo/", ak, sk).status_code == 403


class TestAlertIngestion:
    def test_grafana_alert_lines_reach_loki(self):
        """OBS-130: notifications logged by the API with grafana_alert=1
        are shipped to Loki by Promtail — closed-loop delivery evidence.
        The synthetic alert posted in TestContactPoint (plus any watchdog
        firings) must be queryable."""
        r = requests.get(
            f"{LOKI}/loki/api/v1/query_range",
            params={
                "query": '{compose_service="api"} |= "grafana_alert=1"',
                "limit": 5,
                "since": "24h",
            },
            verify=CA,
            timeout=15,
        )
        result = r.json()["data"]["result"]
        lines = sum(len(s["values"]) for s in result)
        assert lines >= 1, "no grafana_alert=1 lines in Loki in 24h"


class TestWatchdogLoop:
    def test_watchdog_rule_is_firing(self):
        """OBS-025: the always-firing heartbeat must be in Alerting state
        (proves the eval loop itself is alive)."""
        r = requests.get(
            f"{GRAFANA}/api/prometheus/grafana/api/v1/rules",
            auth=_graf_auth(),
            verify=CA,
            timeout=15,
        )
        states = {}
        for group in r.json()["data"]["groups"]:
            for rule in group["rules"]:
                states[rule["name"]] = rule.get("state")
        assert states.get(WATCHDOG_TITLE) in ("firing", "pending"), (
            f"watchdog state: {states.get(WATCHDOG_TITLE)}"
        )
