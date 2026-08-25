"""Shuffle-side setup: environment, workflow registration, hook, indices.

Handles everything that happens *after* the workflow definition is
built: ensuring the 'Shuffle' environment exists, creating the workflow,
fixing branches/startnode, registering the webhook hook in ES, and
creating the soar-alerts / soar-metrics indices.
"""

# NOTE: All ``requests`` calls in this module use ``verify=False`` because
# the lab uses self-signed certificates in the internal Docker network.
# This is safe in the lab context but must NOT be used in production.

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import uuid
from typing import Any

import requests

from soar_lab.common.constants import CONTENT_TYPE_JSON, HEADER_CONTENT_TYPE

from . import config
from .workflow_actions import ACT_NORMALIZE

logger = logging.getLogger(__name__)


def ensure_shuffle_environment(session: requests.Session) -> str:
    """Get active org and ensure 'Shuffle' environment exists.

    Returns org_id.
    """
    logger.info("Getting active organization...")
    org_id = ""
    try:
        me = session.get(f"{config.SHUFFLE_URL}/api/v1/users/me", timeout=15).json()
        active_org = me.get("active_org", {})
        if isinstance(active_org, dict):
            org_id = active_org.get("id", "")
        if not org_id:
            org_id = me.get("orgs", [""])[0]
    except Exception as e:
        logger.warning("Could not get active org: %s", e)

    logger.info("Verifying 'Shuffle' environment in Elasticsearch...")
    es_auth = (
        (config.SHUFFLE_DATA_USER, config.SHUFFLE_DATA_PASS)
        if config.SHUFFLE_DATA_USER and config.SHUFFLE_DATA_PASS
        else None
    )
    try:
        env_id = None
        env_search = requests.get(
            f"{config.SHUFFLE_DATA_URL}/environments/_search?q=Name:Shuffle",
            timeout=15,
            auth=es_auth,
            verify=False,
        )
        if env_search.status_code == 200:
            hits = env_search.json().get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source", {})
                if src.get("Name") == "Shuffle" and (not org_id or src.get("org_id") == org_id):
                    env_id = hit.get("_id")
                    org_id = src.get("org_id", org_id)
                    logger.info("'Shuffle' environment found: %s (org=%s)", env_id, org_id)
                    break
        if not env_id:
            if not org_id:
                try:
                    _orgs = requests.get(
                        f"{config.SHUFFLE_DATA_URL}/organizations/_search?size=1",
                        timeout=10,
                        auth=es_auth,
                        verify=False,
                    ).json()
                    org_id = (
                        _orgs.get("hits", {}).get("hits", [{}])[0].get("_source", {}).get("id", "")
                    )
                except Exception as _e:
                    pass
            if not org_id:
                org_id = str(uuid.uuid4())
            env_id = str(uuid.uuid4())
            idx_check = requests.get(
                f"{config.SHUFFLE_DATA_URL}/environments", timeout=10, auth=es_auth, verify=False
            )
            if idx_check.status_code == 404:
                requests.put(
                    f"{config.SHUFFLE_DATA_URL}/environments",
                    json={"settings": {"number_of_replicas": 0, "number_of_shards": 1}},
                    timeout=15,
                    auth=es_auth,
                    verify=False,
                )
            env_doc = {
                "Name": "Shuffle",
                "Type": "onprem",
                "Registered": True,
                "default": True,
                "archived": False,
                "id": env_id,
                "org_id": org_id,
                "created": int(time.time()),
                "edited": int(time.time()),
            }
            r_env = requests.put(
                f"{config.SHUFFLE_DATA_URL}/environments/_doc/{env_id}",
                json=env_doc,
                timeout=15,
                auth=es_auth,
                verify=False,
            )
            logger.info(
                "'Shuffle' environment created: HTTP %d (id=%s, org=%s)",
                r_env.status_code,
                env_id,
                org_id,
            )
    except Exception as e:
        logger.warning("Could not verify/create 'Shuffle' environment: %s", e)

    return org_id


def create_workflow(session: requests.Session, wf_def: dict[str, Any]) -> dict[str, Any]:
    """Create the workflow in Shuffle.

    Returns the workflow JSON.
    """
    logger.info("Creating workflow '%s'...", config.WF_NAME)
    cr = session.post(f"{config.SHUFFLE_URL}/api/v1/workflows", json=wf_def, timeout=120)
    if not cr.ok:
        logger.error("creating workflow: HTTP %d %s", cr.status_code, cr.text[:300])
        raise RuntimeError(f"Failed to create workflow: HTTP {cr.status_code}")
    wf = cr.json()
    logger.info("Workflow created: %s", wf["id"])
    return wf


def fix_branches_and_startnode(
    session: requests.Session, wf_id: str, trigger_id: str
) -> tuple[str, list[str]]:
    """Fix branches so trigger→normalize and normalize→fanout.

    Returns (org_id, thehive_children).
    """
    wf_detail = session.get(f"{config.SHUFFLE_URL}/api/v1/workflows/{wf_id}", timeout=60).json()
    org_id = wf_detail.get("org_id", "")
    thehive_children: list[str] = []
    for b in wf_detail.get("branches", []):
        dst = b.get("destination_id", "")
        src = b.get("source_id", "")
        if src == "webhook_trigger":
            b["source_id"] = trigger_id
        elif src == trigger_id and dst != ACT_NORMALIZE:
            b["source_id"] = ACT_NORMALIZE
            thehive_children.append(dst)

    wf_detail["start"] = ACT_NORMALIZE
    for a in wf_detail.get("actions", []):
        a["isStartNode"] = a.get("id") == ACT_NORMALIZE
    for t in wf_detail.get("triggers", []):
        if t["id"] == trigger_id:
            t["status"] = "running"
            t["isStartNode"] = False
    wf_detail["status"] = "active"
    wf_detail["active"] = True
    r_put = session.put(
        f"{config.SHUFFLE_URL}/api/v1/workflows/{wf_id}", json=wf_detail, timeout=120
    )
    logger.info(
        "Branches and startnode updated: HTTP %d (thehive children: %d)",
        r_put.status_code,
        len(thehive_children),
    )

    # Patch ES indices (workflow + workflow_revisions)
    _patch_es_workflow_docs(wf_id, trigger_id)
    return org_id, thehive_children


def _patch_es_workflow_docs(wf_id: str, trigger_id: str) -> None:
    """Force start node and branches in Elasticsearch workflow/revisions
    indices."""
    logger.info("Forcing start node (start=ACT_NORMALIZE) and branches in Elasticsearch...")
    es_auth = (
        (config.SHUFFLE_DATA_USER, config.SHUFFLE_DATA_PASS)
        if config.SHUFFLE_DATA_USER and config.SHUFFLE_DATA_PASS
        else None
    )

    def _patch_wf_doc(index, doc_id):
        r = requests.get(
            f"{config.SHUFFLE_DATA_URL}/{index}/_doc/{doc_id}",
            timeout=10,
            auth=es_auth,
            verify=False,
        )
        if r.status_code != 200:
            return r.status_code
        src = r.json().get("_source", {})
        src["start"] = ACT_NORMALIZE
        for _a in src.get("actions", []):
            _a["isStartNode"] = _a.get("id") == ACT_NORMALIZE
        for _t in src.get("triggers", []):
            _t["isStartNode"] = False
        for _b in src.get("branches", []):
            if _b.get("source_id") == trigger_id and _b.get("destination_id") != ACT_NORMALIZE:
                _b["source_id"] = ACT_NORMALIZE
        rp = requests.put(
            f"{config.SHUFFLE_DATA_URL}/{index}/_doc/{doc_id}",
            json=src,
            timeout=15,
            auth=es_auth,
            verify=False,
        )
        return rp.status_code

    try:
        _wf_idx_res = requests.get(
            f"{config.SHUFFLE_DATA_URL}/_cat/indices/workflow-*?h=index",
            timeout=10,
            auth=es_auth,
            verify=False,
        )
        _wf_index = (_wf_idx_res.text.strip().split("\n") + ["workflow-000001"])[
            0
        ] or "workflow-000001"
        _sc1 = _patch_wf_doc(_wf_index, wf_id)
        logger.info("ES workflow start updated (%s): HTTP %d", _wf_index, _sc1)

        _rev_idx_res = requests.get(
            f"{config.SHUFFLE_DATA_URL}/_cat/indices/workflow_revisions-*?h=index",
            timeout=10,
            auth=es_auth,
            verify=False,
        )
        _rev_index = (_rev_idx_res.text.strip().split("\n") + ["workflow_revisions-000001"])[
            0
        ] or "workflow_revisions-000001"
        _hits = []
        for _attempt in range(4):
            _rev_search = requests.post(
                f"{config.SHUFFLE_DATA_URL}/{_rev_index}/_search",
                json={
                    "query": {
                        "bool": {
                            "should": [{"term": {"id.keyword": wf_id}}, {"match": {"id": wf_id}}]
                        }
                    },
                    "size": 5,
                },
                timeout=10,
                auth=es_auth,
                verify=False,
            )
            if _rev_search.status_code == 200:
                _hits = _rev_search.json().get("hits", {}).get("hits", [])
            if not _hits:
                _rev_all = requests.get(
                    f"{config.SHUFFLE_DATA_URL}/{_rev_index}/_search?size=50",
                    timeout=10,
                    auth=es_auth,
                    verify=False,
                )
                _hits = [
                    _h
                    for _h in _rev_all.json().get("hits", {}).get("hits", [])
                    if _h.get("_source", {}).get("id") == wf_id
                ]
            if _hits:
                break
            logger.warning("Workflow revision not found in ES yet, retrying... (%ds)", _attempt * 5)
            time.sleep(5)
        if _hits:
            _rev_doc_id = _hits[0]["_id"]
            _sc2 = _patch_wf_doc(_rev_index, _rev_doc_id)
            logger.info(
                "ES revision start updated (%s/%s): HTTP %d", _rev_index, _rev_doc_id[:8], _sc2
            )
        else:
            logger.warning("Workflow revision not found in ES")
    except Exception as e:
        logger.warning("Could not force start in ES: %s", e)


def delete_old_workflows(
    session: requests.Session, old_workflow_ids: list[str], new_wf_id: str
) -> None:
    """Delete previous workflows with the same name (after the new one is
    created)."""
    for old_id in old_workflow_ids:
        if old_id != new_wf_id:
            try:
                session.delete(f"{config.SHUFFLE_URL}/api/v1/workflows/{old_id}", timeout=30)
                logger.info("Deleted previous workflow: %s", old_id)
            except Exception as e:
                logger.warning("Could not delete previous workflow %s: %s", old_id, e)


def register_hook_in_es(trigger_id: str, wf_id: str, org_id: str) -> None:
    """Register the webhook hook in Elasticsearch via docker exec."""
    logger.info("Registering hook in Elasticsearch...")
    hook_doc = {
        "id": trigger_id,
        "start": wf_id,
        "type": "webhook",
        "owner": "",
        "status": "running",
        "workflows": [wf_id],
        "running": True,
        "org_id": org_id,
        "environment": "Shuffle",
        "info": {},
        "actions": [],
    }
    try:
        hook_json = json.dumps(hook_doc)
        cmd = [
            "docker",
            "exec",
            "soar_opensearch",
            "curl",
            "-s",
            "-X",
            "PUT",
            f"http://localhost:9200/hooks/_doc/{trigger_id}",
            "-H",
            "Content-Type: application/json",
            "-d",
            hook_json,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # nosec B603
        if res.returncode == 0:
            logger.info("Hook in ES: %s", res.stdout)
        else:
            logger.error("Hook in ES: Error - %s", res.stderr)
    except Exception as e:
        logger.error("Hook in ES: Error - %s", e)
    logger.info("Hook registered correctly (no backend restart needed).")


def ensure_es_indices() -> None:
    """Create soar-alerts and soar-metrics indices if they don't exist."""
    es_auth = (config.ES_USER, config.ES_PASS) if config.ES_USER and config.ES_PASS else None

    # soar-alerts
    try:
        r_idx = requests.get(f"{config.ES_URL}/soar-alerts", timeout=10, auth=es_auth, verify=False)
        if r_idx.status_code == 404:
            create = requests.put(
                f"{config.ES_URL}/soar-alerts",
                json={"settings": {"number_of_replicas": 0, "number_of_shards": 1}},
                timeout=15,
                auth=es_auth,
                verify=False,
            )
            logger.info("soar-alerts index created: HTTP %d", create.status_code)
        else:
            logger.info("soar-alerts index already exists.")
    except Exception as _e:
        logger.warning("could not create soar-alerts: %s", _e)

    # soar-metrics
    try:
        r_metrics = requests.get(
            f"{config.ES_URL}/soar-metrics", timeout=10, auth=es_auth, verify=False
        )
        if r_metrics.status_code == 404:
            metrics_mapping = {
                "settings": {"number_of_replicas": 0, "number_of_shards": 1},
                "mappings": {
                    "properties": {
                        "alert_id": {"type": "keyword"},
                        "alert_type": {"type": "keyword"},
                        "severity": {"type": "integer"},
                        "mttr_seconds": {"type": "float"},
                        "@timestamp": {"type": "date"},
                        "timestamp": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "metric_type": {"type": "keyword"},
                        "thehive_case_id": {"type": "keyword"},
                        "cortex_hash_job": {"type": "text"},
                        "cortex_ip_job": {"type": "text"},
                        "misp_results": {"type": "text"},
                    }
                },
            }
            create_m = requests.put(
                f"{config.ES_URL}/soar-metrics",
                json=metrics_mapping,
                timeout=15,
                auth=es_auth,
                verify=False,
            )
            logger.info("soar-metrics index created with mapping: HTTP %d", create_m.status_code)
        else:
            logger.info("soar-metrics index already exists.")
    except Exception as _e:
        logger.warning("could not create soar-metrics: %s", _e)


def import_grafana_dashboard() -> None:
    """Import the Grafana KPI dashboard."""
    logger.info("Importing Grafana KPI dashboard...")
    grafana_url = os.environ.get("GRAFANA_URL", "http://grafana:3000")
    grafana_user = os.environ.get("GRAFANA_ADMIN_USER", "admin")
    grafana_pass = os.environ.get("GRAFANA_ADMIN_PASSWORD", "")

    if os.path.exists("/app/infra/docker/compose/logging/kpi-dashboard.json"):
        kpi_dashboard_path = "/app/infra/docker/compose/logging/kpi-dashboard.json"
    else:
        kpi_dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "infra",
            "docker",
            "compose",
            "logging",
            "kpi-dashboard.json",
        )

    try:
        with open(kpi_dashboard_path) as f:
            dashboard = json.load(f)
        grafana_response = requests.post(
            f"{grafana_url}/api/dashboards/db",
            auth=(grafana_user, grafana_pass),
            json=dashboard,
            headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
            timeout=15,
            verify=False,
        )
        if grafana_response.status_code == 200:
            result = grafana_response.json()
            logger.info("KPI dashboard imported successfully:")
            logger.info("UID: %s", result.get("uid"))
            logger.info("URL: %s", result.get("url"))
            logger.info("ID: %s", result.get("id"))
        else:
            logger.warning("Could not import KPI dashboard: HTTP %d", grafana_response.status_code)
            logger.warning("Response: %s", grafana_response.text[:200])
    except FileNotFoundError:
        logger.warning("kpi-dashboard.json file not found at %s", kpi_dashboard_path)
    except Exception as e:
        logger.warning("Error importing KPI dashboard: %s", e)


def save_webhook_info(
    trigger_id: str, wf_id: str, org_id: str, webhook_url_internal: str, webhook_url: str
) -> None:
    """Save webhook_info.json for E2E tests."""
    default_info_dir = (
        "/app/reports/validation/results"
        if os.path.isdir("/app")
        else os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "reports",
            "validation",
            "results",
        )
    )
    info_path = os.path.join(
        os.environ.get("WEBHOOK_INFO_DIR", default_info_dir), "webhook_info.json"
    )
    os.makedirs(os.path.dirname(info_path), exist_ok=True)
    webhook_info = {
        "webhook_url": webhook_url_internal,
        "webhook_url_host": webhook_url,
        "workflow_id": wf_id,
        "trigger_id": trigger_id,
        "org_id": org_id,
        "workflow_name": config.WF_NAME,
        "actions": {
            "thehive": f"{config.THEHIVE_URL} - create case",
            "cortex_hash": f"{config.CORTEX_URL} - analyze hash",
            "cortex_ip": f"{config.CORTEX_URL} - analyze IP",
            "misp": f"{config.MISP_URL} - search IOC",
            "elasticsearch": f"{config.ES_URL}/soar-alerts - index alert",
        },
    }
    try:
        with open(info_path, "w") as f:
            json.dump(webhook_info, f, indent=2)
        if os.path.exists("/app"):
            app_path = "/app/webhook_info.json"
            try:
                with open(app_path, "w") as f:
                    json.dump(webhook_info, f, indent=2)
                logger.info("Copied to %s for E2E tests", app_path)
            except Exception as e:
                logger.warning("Could not copy to %s: %s", app_path, e)
        # Sync SIEM_WEBHOOK_TOKEN in .env.full so the simulator picks up the
        # new webhook trigger_id (the simulator builds the URL from this token).
        _sync_siem_webhook_token(trigger_id)
    except Exception as e:
        logger.warning("Error writing %s: %s", info_path, e)
        tmp_path = "/tmp/webhook_info.json"
        with open(tmp_path, "w") as f:
            json.dump(webhook_info, f, indent=2)
        logger.warning("Written to %s", tmp_path)
        logger.warning("Run: docker cp soar_api:%s %s", tmp_path, info_path)


def _sync_siem_webhook_token(trigger_id: str) -> None:
    """Update SIEM_WEBHOOK_TOKEN in .env.full with the new trigger_id.

    The simulator (``soar_lab.simulator.simulate_alerts``) builds the webhook
    URL from ``SIEM_WEBHOOK_TOKEN`` via ``SHUFFLE_WEBHOOK_TEMPLATE``.  After a
    ``make reset`` the old token is stale, so we must sync it here.
    """
    import re

    env_path = config.ENV_FILE
    if not env_path or not os.path.exists(env_path):
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            content = f.read()
        new_line = f"SIEM_WEBHOOK_TOKEN=webhook_{trigger_id}"
        if re.search(r"^SIEM_WEBHOOK_TOKEN=.*$", content, re.MULTILINE):
            content = re.sub(r"^SIEM_WEBHOOK_TOKEN=.*$", new_line, content, flags=re.MULTILINE)
        else:
            content = content.rstrip() + "\n" + new_line + "\n"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.environ["SIEM_WEBHOOK_TOKEN"] = f"webhook_{trigger_id}"
        logger.info("  SIEM_WEBHOOK_TOKEN synced in .env.full (webhook_%s)", trigger_id)
    except Exception as e:
        logger.warning("  Could not sync SIEM_WEBHOOK_TOKEN in .env.full: %s", e)
