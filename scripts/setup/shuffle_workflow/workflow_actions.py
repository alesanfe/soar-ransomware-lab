"""Action Factory — define each individual Shuffle workflow action.

Each action is built independently and then assembled in
:mod:`workflow_definition`.  Embedded Python scripts are loaded as
text via :mod:`script_loader` so they live as real ``.py`` files in
``shuffle_workflow/scripts/``.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from typing import Any

from . import config, script_loader
from .utils import action, branch, execute_python_action, param, pos

logger = logging.getLogger(__name__)


# ── Action IDs (stable identifiers Shuffle depends on) ────────────────────────
ACT_NORMALIZE = "act_normalize_inputs"
ACT_BUILD_CASE_JSON = "act_build_case_json"
ACT_THEHIVE = "act_thehive_create_case"
ACT_THEHIVE_TASK = "act_thehive_add_task"
ACT_VERIFY_TASK = "act_verify_task"
ACT_CALC_TASK_TITLE = "act_calc_task_title"
ACT_THEHIVE_OBS_HASH = "act_thehive_obs_hash"
ACT_VERIFY_OBS_HASH = "act_verify_obs_hash"
ACT_THEHIVE_OBS_IP = "act_thehive_obs_ip"
ACT_VERIFY_OBS_IP = "act_verify_obs_ip"
ACT_CORTEX_HASH = "act_cortex_hash"
ACT_VERIFY_CORTEX_HASH = "act_verify_cortex_hash"
ACT_CORTEX_IP = "act_cortex_ip"
ACT_VERIFY_CORTEX_IP = "act_verify_cortex_ip"
ACT_MISP_CREATE = "act_misp_create_event"
ACT_MISP = "act_misp_search"
ACT_VERIFY_MISP = "act_verify_misp"
ACT_BUILD_ES_JSON = "act_build_es_json"
ACT_ES = "act_es_index"
ACT_VERIFY_ES = "act_verify_es"
ACT_CALC_MTTR = "act_calc_mttr"
ACT_INDEX_METRICS = "act_index_metrics"
ACT_BUILD_METRICS_JSON = "act_build_metrics_json"
ACT_CORTEX_HASH_VIRUSSHARE = "act_cortex_hash_virusshare"
ACT_CORTEX_IP_DSHIELD = "act_cortex_ip_dshield"
ACT_CORTEX_IP_MNEMONIC_PDNS = "act_cortex_ip_mnemonic_pdns"
ACT_CORTEX_IP_GOOGLEDNS = "act_cortex_ip_googledns"
ACT_CORTEX_IP_IPAPI = "act_cortex_ip_ipapi"
ACT_TENZIR_ANALYZE = "act_tenzir_analyze"
ACT_TENZIR_SERVE = "act_tenzir_serve"
ACT_NETWORK_WATCH = "act_network_watch"
ACT_REDIS_CACHE = "act_redis_cache"
ACT_LOKI_SEARCH = "act_loki_search"
ACT_VERIFY_TENZIR = "act_verify_tenzir"
ACT_VERIFY_NETWORK = "act_verify_network"
ACT_VERIFY_REDIS = "act_verify_redis"
ACT_VERIFY_LOKI = "act_verify_loki"
ACT_CALC_DECISION = "act_calc_decision"
ACT_CONTAINMENT = "act_containment"
ACT_MARK_FP = "act_mark_false_positive"
ACT_UPDATE_INPROGRESS = "act_update_inprogress"
ACT_NOTIFY_CRITICAL = "act_notify_critical"
ACT_NOTIFY_INFO = "act_notify_info"
ACT_BUILD_HIVE_SUMMARY = "act_build_hive_summary"
ACT_ENRICH_CASE = "act_enrich_case"

TRIGGER_NODE = "webhook_trigger"


@dataclass
class WorkflowContext:
    """Resolved keys, IDs and runtime values needed to build the workflow."""

    # API keys
    thehive_key: str
    cortex_key: str
    misp_key: str
    # App IDs (resolved from Shuffle)
    app_id_http: str
    app_id_shuffle_tools: str
    # Cortex basic auth (base64)
    cortex_basic: str
    # ES basic auth (base64)
    es_basic: str
    # Selected analyzer IDs
    hash_analyzer_id: str = "Hashdd_Status"
    ip_analyzer_id: str = "IP-API"
    hash_virusshare_id: str = "Virusshare_2_0"
    ip_dshield_id: str = "DShield_lookup"
    ip_mnemonic_pdns_id: str = "Mnemonic_pDNS_Public"
    ip_googledns_id: str = "GoogleDNS_resolve"
    ip_ipapi_id: str = "IP-API"
    # Availability flags for secondary analyzers
    has_hash_virusshare: bool = False
    has_ip_dshield: bool = False
    has_ip_mnemonic_pdns: bool = False
    has_ip_googledns: bool = False
    has_ip_ipapi: bool = False
    # Dynamic Cortex actions/branches (auto-wired from installed analyzers)
    dynamic_cortex_actions: list[dict[str, Any]] = field(default_factory=list)
    dynamic_cortex_branches: list[dict[str, Any]] = field(default_factory=list)
    # Loki query time range (nanoseconds)
    loki_start_ns: int = 0
    loki_end_ns: int = 0


def _es_basic_auth() -> str:
    """Build the ES Basic auth header value."""
    return base64.b64encode(f"{config.ES_USER}:{config.ES_PASS}".encode()).decode()


def _cortex_basic_auth() -> str:
    """Build the Cortex Basic auth header value from the latest .env.full."""
    from .credentials import fetch_password_from_env

    cortex_pass = fetch_password_from_env("CORTEX_ADMIN_PASSWORD", config.CORTEX_ADMIN_PASS)
    cortex_user = fetch_password_from_env("CORTEX_ADMIN_USER", config.CORTEX_ADMIN_USER)
    return base64.b64encode(f"{cortex_user}:{cortex_pass}".encode()).decode()


def build_actions(ctx: WorkflowContext) -> list[dict[str, Any]]:
    """Build the complete list of workflow action nodes."""
    load = script_loader.load_script

    actions_list: list[dict[str, Any]] = [
        # ── Node 0. normalize_inputs ─────────────────────────────────────────
        execute_python_action(
            ACT_NORMALIZE,
            "normalize_inputs",
            load("normalize_inputs"),
            pos(250, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 0b. build_case_json ─────────────────────────────────────────
        execute_python_action(
            ACT_BUILD_CASE_JSON,
            "build_case_json",
            load("build_case_json"),
            pos(300, -50),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 1. TheHive: create case ─────────────────────────────────────
        action(
            ACT_THEHIVE,
            "thehive_create_case",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.THEHIVE_INT}/api/case"),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Bearer {ctx.thehive_key}",
                ),
                param("body", "$build_case_json.message"),
                param("timeout", "120"),
            ],
            pos(300, 0),
            app_id=ctx.app_id_http,
        ),
        # ── Node 2c. calc_task_title ─────────────────────────────────────────
        execute_python_action(
            ACT_CALC_TASK_TITLE,
            "calc_task_title",
            load("calc_task_title"),
            pos(300, -200),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 3. TheHive: add hash observable ─────────────────────────────
        action(
            ACT_THEHIVE_OBS_HASH,
            "thehive_obs_hash",
            "http",
            "1.0.0",
            "POST",
            [
                param(
                    "url", f"{config.THEHIVE_INT}/api/case/$thehive_create_case.body._id/artifact"
                ),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Bearer {ctx.thehive_key}",
                ),
                param(
                    "body",
                    '{"dataType":"hash","data":"$exec.hash",'
                    '"message":"Process hash from ransomware alert",'
                    '"tlp":2,"ioc":true,"tags":["ransomware","hash"]}',
                ),
                param("timeout", "120"),
            ],
            pos(300, -150),
            app_id=ctx.app_id_http,
        ),
        # ── Node 4. TheHive: add IP observable ───────────────────────────────
        action(
            ACT_THEHIVE_OBS_IP,
            "thehive_obs_ip",
            "http",
            "1.0.0",
            "POST",
            [
                param(
                    "url", f"{config.THEHIVE_INT}/api/case/$thehive_create_case.body._id/artifact"
                ),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Bearer {ctx.thehive_key}",
                ),
                param(
                    "body",
                    '{"dataType":"ip","data":"$exec.src_ip",'
                    '"message":"Source IP from ransomware alert",'
                    '"tlp":2,"ioc":true,"tags":["ransomware","ip"]}',
                ),
                param("timeout", "120"),
            ],
            pos(300, 150),
            app_id=ctx.app_id_http,
        ),
        # ── Node 2. TheHive: add investigation task ──────────────────────────
        action(
            ACT_THEHIVE_TASK,
            "thehive_add_task",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.THEHIVE_INT}/api/case/$thehive_create_case.body._id/task"),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Bearer {ctx.thehive_key}",
                ),
                param(
                    "body",
                    '{"title":"$calc_task_title.message",'
                    '"description":"Analyze hash and IP with Cortex and MISP.'
                    ' Contain and preserve evidence.",'
                    '"status":"Waiting","order":0,"flag":false}',
                ),
                param("timeout", "120"),
            ],
            pos(300, -250),
            app_id=ctx.app_id_http,
        ),
        # ── Node 5. Cortex: hash job ─────────────────────────────────────────
        action(
            ACT_CORTEX_HASH,
            "cortex_hash",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.hash_analyzer_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.hash", "attributes": {"dataType": "hash", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, -200),
            app_id=ctx.app_id_http,
        ),
        # ── Node 12. Cortex: hash with Virusshare ────────────────────────────
        action(
            ACT_CORTEX_HASH_VIRUSSHARE,
            "cortex_hash_virusshare",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.hash_virusshare_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.hash", "attributes": {"dataType": "hash", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, -300),
            app_id=ctx.app_id_http,
        ),
        # ── Node 5b. verify_cortex_hash ──────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_CORTEX_HASH,
            "verify_cortex_hash",
            load("verify_cortex_hash"),
            pos(990, -200),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 6. Cortex: IP job ───────────────────────────────────────────
        action(
            ACT_CORTEX_IP,
            "cortex_ip",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.ip_analyzer_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, 0),
            app_id=ctx.app_id_http,
        ),
        # ── Node 14. Cortex: IP with DShield ──────────────────────────────────
        action(
            ACT_CORTEX_IP_DSHIELD,
            "cortex_ip_dshield",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.ip_dshield_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, 100),
            app_id=ctx.app_id_http,
        ),
        # ── Node 17. Cortex: IP with IP-API ──────────────────────────────────
        action(
            ACT_CORTEX_IP_IPAPI,
            "cortex_ip_ipapi",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.ip_ipapi_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, 200),
            app_id=ctx.app_id_http,
        ),
        # ── Node 15. Cortex: IP with Mnemonic pDNS Public ─────────────────────
        action(
            ACT_CORTEX_IP_MNEMONIC_PDNS,
            "cortex_ip_mnemonic_pdns",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.ip_mnemonic_pdns_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, 300),
            app_id=ctx.app_id_http,
        ),
        # ── Node 16. Cortex: IP with GoogleDNS ───────────────────────────────
        action(
            ACT_CORTEX_IP_GOOGLEDNS,
            "cortex_ip_googledns",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.CORTEX_INT}/api/analyzer/{ctx.ip_googledns_id}/run"),
                param(
                    "headers",
                    "Content-Type: application/json\nAuthorization: Basic " + ctx.cortex_basic,
                ),
                param(
                    "body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'
                ),
                param("timeout", "120"),
            ],
            pos(950, 400),
            app_id=ctx.app_id_http,
        ),
        # ── Node 6b. verify_cortex_ip ────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_CORTEX_IP,
            "verify_cortex_ip",
            load("verify_cortex_ip"),
            pos(990, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 7. MISP: create event ───────────────────────────────────────
        action(
            ACT_MISP_CREATE,
            "misp_create",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.MISP_INT}/events"),
                param(
                    "headers",
                    "Content-Type: application/json\nAccept: application/json\nAuthorization: "
                    + ctx.misp_key,
                ),
                param(
                    "body",
                    '{"info": "SOAR alert $exec.alert_id",'
                    ' "threat_level_id": 3, "analysis": 0, "distribution": 0, '
                    '"Attribute": [{"type": "sha256", "value": "$exec.hash",'
                    ' "to_ids": true}, {"type": "ip-dst",'
                    ' "value": "$exec.src_ip", "to_ids": true}]}',
                ),
                param("verify", "false"),
                param("timeout", "180"),
            ],
            pos(940, 200),
            app_id=ctx.app_id_http,
        ),
        # ── Node 7a. MISP: search hash ───────────────────────────────────────
        action(
            ACT_MISP,
            "misp_search",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.MISP_INT}/attributes/restSearch"),
                param("headers", "Content-Type: application/json\nAuthorization: " + ctx.misp_key),
                param(
                    "body",
                    '{"returnFormat": "json", "value": "$exec.hash",'
                    ' "type": ["md5", "sha1", "sha256"], "limit": 10}',
                ),
                param("verify", "false"),
                param("timeout", "180"),
            ],
            pos(950, 200),
            app_id=ctx.app_id_http,
        ),
        # ── Node 7b. verify_misp ─────────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_MISP,
            "verify_misp",
            load("verify_misp"),
            pos(990, 200),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 7b. build_es_json ────────────────────────────────────────────
        execute_python_action(
            ACT_BUILD_ES_JSON,
            "build_es_json",
            load("build_es_json"),
            pos(1190, -100),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 8. ES: index alert ──────────────────────────────────────────
        action(
            ACT_ES,
            "es_index",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.ES_INT}/soar-alerts/_doc/$exec.alert_id"),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Basic {ctx.es_basic}",
                ),
                param("body", "$build_es_json.message"),
                param("timeout", "180"),
            ],
            pos(1200, -100),
            app_id=ctx.app_id_http,
        ),
        # ── Node 8b. verify_es ───────────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_ES,
            "verify_es",
            load("verify_es"),
            pos(1240, -100),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 2b. verify_task ─────────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_TASK,
            "verify_task",
            load("verify_task"),
            pos(700, -150),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 3b. verify_obs_hash ─────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_OBS_HASH,
            "verify_obs_hash",
            load("verify_obs_hash"),
            pos(700, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 4b. verify_obs_ip ───────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_OBS_IP,
            "verify_obs_ip",
            load("verify_obs_ip"),
            pos(700, 150),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 10. calc_mttr ───────────────────────────────────────────────
        execute_python_action(
            ACT_CALC_MTTR,
            "calc_mttr",
            load("calc_mttr"),
            pos(1400, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 30. build_hive_summary ──────────────────────────────────────
        execute_python_action(
            ACT_BUILD_HIVE_SUMMARY,
            "build_hive_summary",
            load("build_hive_summary"),
            pos(1700, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 31. TheHive: enrich case ────────────────────────────────────
        action(
            ACT_ENRICH_CASE,
            "enrich_case",
            "http",
            "1.0.0",
            "PATCH",
            [
                param("url", f"{config.THEHIVE_INT}/api/case/$thehive_create_case.body._id"),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Bearer {ctx.thehive_key}",
                ),
                param(
                    "body",
                    '{"description": "$build_hive_summary.message",'
                    ' "tags": ["ransomware", "soar-lab", "analyzed",'
                    ' "tenzir", "network-watcher", "redis", "loki",'
                    ' "mttr-calculated"]}',
                ),
                param("timeout", "120"),
            ],
            pos(1800, 0),
            app_id=ctx.app_id_http,
        ),
        # ── Node 11b. build_metrics_json ─────────────────────────────────────
        execute_python_action(
            ACT_BUILD_METRICS_JSON,
            "build_metrics_json",
            load("build_metrics_json"),
            pos(1650, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 11. ES: index metrics ───────────────────────────────────────
        # Use alert_id as document ID for idempotency (prevents duplicates on retries)
        action(
            ACT_INDEX_METRICS,
            "es_index_metrics",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.ES_INT}/soar-metrics/_doc/$exec.alert_id"),
                param(
                    "headers",
                    f"Content-Type: application/json\nAuthorization: Basic {ctx.es_basic}",
                ),
                param("body", "$build_metrics_json.message"),
                param("timeout", "180"),
            ],
            pos(1600, 0),
            app_id=ctx.app_id_http,
        ),
        # ── Node 18. Tenzir: create pipeline ─────────────────────────────────
        action(
            ACT_TENZIR_ANALYZE,
            "tenzir_analyze",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.TENZIR_URL}/api/v0/pipeline/create"),
                param("headers", "Content-Type: application/json"),
                param(
                    "body",
                    '{"definition": "export | where hostname == \\"$exec.hostname\\" or '
                    'src_ip == \\"$exec.src_ip\\" | head 100 | serve \\"$exec.alert_id\\"", '
                    '"name": "tenzir-$exec.alert_id", "hidden": true, "ttl": "30s", '
                    '"autostart": {"created": true}}',
                ),
                param("verify", "false"),
                param("timeout", "30"),
            ],
            pos(1600, -200),
            app_id=ctx.app_id_http,
        ),
        # ── Node 18b. Tenzir: fetch served results ───────────────────────────
        action(
            ACT_TENZIR_SERVE,
            "tenzir_serve",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.TENZIR_URL}/api/v0/serve"),
                param("headers", "Content-Type: application/json"),
                param(
                    "body",
                    '{"serve_id": "$exec.alert_id", "continuation_token": null, '
                    '"timeout": "3s", "max_events": 100}',
                ),
                param("verify", "false"),
                param("timeout", "30"),
            ],
            pos(1600, -150),
            app_id=ctx.app_id_http,
        ),
        # ── Node 19. Network Watcher ─────────────────────────────────────────
        action(
            ACT_NETWORK_WATCH,
            "network_watch",
            "http",
            "1.0.0",
            "GET",
            [
                param(
                    "url",
                    "http://network-watcher:8080/api/connections?ip=$exec.src_ip&limit=50",
                ),
                param("headers", "Content-Type: application/json"),
                param("verify", "false"),
                param("timeout", "180"),
            ],
            pos(1600, -100),
            app_id=ctx.app_id_http,
        ),
        # ── Node 20. Redis: cache IoCs ───────────────────────────────────────
        action(
            ACT_REDIS_CACHE,
            "redis_cache",
            "http",
            "1.0.0",
            "POST",
            [
                param("url", f"{config.API_URL}/api/v1/cache/ioc"),
                param("headers", "Content-Type: application/json"),
                param(
                    "body",
                    '{"key": "ioc:$exec.hash", "value": "$exec.alert_id", "ttl_seconds": 3600}',
                ),
                param("verify", "false"),
                param("timeout", "180"),
            ],
            pos(1600, 100),
            app_id=ctx.app_id_http,
        ),
        # ── Node 21. Loki: search logs ───────────────────────────────────────
        action(
            ACT_LOKI_SEARCH,
            "loki_search",
            "http",
            "1.0.0",
            "GET",
            [
                param(
                    "url",
                    f"{config.LOKI_URL}/loki/api/v1/query_range"
                    "?query=%7Bjob%3D~%22.%2B%22%7D%20%7C~%20%22$exec.hostname%7C$exec.src_ip%22"
                    "&limit=100"
                    f"&start={ctx.loki_start_ns}&end={ctx.loki_end_ns}",
                ),
                param("headers", "Content-Type: application/json"),
                param("verify", "false"),
                param("timeout", "180"),
            ],
            pos(1600, 200),
            app_id=ctx.app_id_http,
        ),
        # ── Node 22. verify_tenzir ───────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_TENZIR,
            "verify_tenzir",
            load("verify_tenzir"),
            pos(1640, -200),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 23. verify_network ──────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_NETWORK,
            "verify_network",
            load("verify_network"),
            pos(1640, -100),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 24. verify_redis ────────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_REDIS,
            "verify_redis",
            load("verify_redis"),
            pos(1640, 100),
            ctx.app_id_shuffle_tools,
        ),
        # ── Node 25. verify_loki ─────────────────────────────────────────────
        execute_python_action(
            ACT_VERIFY_LOKI,
            "verify_loki",
            load("verify_loki"),
            pos(1640, 200),
            ctx.app_id_shuffle_tools,
        ),
        # ── N6. calc_decision ────────────────────────────────────────────────
        execute_python_action(
            ACT_CALC_DECISION,
            "calc_decision",
            load("calc_decision"),
            pos(1450, 0),
            ctx.app_id_shuffle_tools,
        ),
        # ── N7. containment (malicious branch) ───────────────────────────────
        execute_python_action(
            ACT_CONTAINMENT,
            "containment",
            load("containment"),
            pos(1500, -200),
            ctx.app_id_shuffle_tools,
        ),
        # ── N8. update_inprogress (malicious branch) ─────────────────────────
        execute_python_action(
            ACT_UPDATE_INPROGRESS,
            "update_inprogress",
            load("update_inprogress"),
            pos(1550, -200),
            ctx.app_id_shuffle_tools,
        ),
        # ── N9. notify_critical (malicious branch) ───────────────────────────
        execute_python_action(
            ACT_NOTIFY_CRITICAL,
            "notify_critical",
            load("notify_critical"),
            pos(1600, -200),
            ctx.app_id_shuffle_tools,
        ),
        # ── N7b. mark_false_positive (benign branch) ─────────────────────────
        # The mark_false_positive script has __THEHIVE_INT__ and __THEHIVE_KEY__
        # placeholders that we substitute with the real values.
        execute_python_action(
            ACT_MARK_FP,
            "mark_false_positive",
            load("mark_false_positive")
            .replace("__THEHIVE_INT__", config.THEHIVE_INT)
            .replace("__THEHIVE_KEY__", ctx.thehive_key),
            pos(1500, 200),
            ctx.app_id_shuffle_tools,
        ),
        # ── N9b. notify_info (benign branch) ─────────────────────────────────
        execute_python_action(
            ACT_NOTIFY_INFO,
            "notify_info",
            load("notify_info"),
            pos(1600, 200),
            ctx.app_id_shuffle_tools,
        ),
    ]

    # Drop secondary Cortex analyzer nodes that are not actually installed
    _unavailable = {
        aid
        for aid, available in (
            (ACT_CORTEX_HASH_VIRUSSHARE, ctx.has_hash_virusshare),
            (ACT_CORTEX_IP_DSHIELD, ctx.has_ip_dshield),
            (ACT_CORTEX_IP_MNEMONIC_PDNS, ctx.has_ip_mnemonic_pdns),
            (ACT_CORTEX_IP_GOOGLEDNS, ctx.has_ip_googledns),
            (ACT_CORTEX_IP_IPAPI, ctx.has_ip_ipapi),
        )
        if not available
    }
    if _unavailable:
        logger.info(
            "  [cortex] Skipping %d node(s) for unavailable analyzers: %s",
            len(_unavailable),
            sorted(_unavailable),
        )
    actions_list = [a for a in actions_list if a["id"] not in _unavailable]
    actions_list.extend(ctx.dynamic_cortex_actions)

    return actions_list


def build_branches(ctx: WorkflowContext) -> list[dict[str, Any]]:
    """Build the complete list of workflow branches (edges)."""
    _unavailable = {
        aid
        for aid, available in (
            (ACT_CORTEX_HASH_VIRUSSHARE, ctx.has_hash_virusshare),
            (ACT_CORTEX_IP_DSHIELD, ctx.has_ip_dshield),
            (ACT_CORTEX_IP_MNEMONIC_PDNS, ctx.has_ip_mnemonic_pdns),
            (ACT_CORTEX_IP_GOOGLEDNS, ctx.has_ip_googledns),
            (ACT_CORTEX_IP_IPAPI, ctx.has_ip_ipapi),
        )
        if not available
    }

    branches_list = [
        # Webhook → normalize inputs
        branch("br_wh_normalize", TRIGGER_NODE, ACT_NORMALIZE),
        # Normalize → build case JSON
        branch("br_normalize_build", ACT_NORMALIZE, ACT_BUILD_CASE_JSON),
        # JSON built → create case
        branch("br_build_thehive", ACT_BUILD_CASE_JSON, ACT_THEHIVE),
        # Case created → observables and task in PARALLEL
        branch("br_hive_obs_hash", ACT_THEHIVE, ACT_THEHIVE_OBS_HASH),
        branch("br_hive_obs_ip", ACT_THEHIVE, ACT_THEHIVE_OBS_IP),
        branch("br_hive_calc_title", ACT_THEHIVE, ACT_CALC_TASK_TITLE),
        branch("br_hive_task", ACT_CALC_TASK_TITLE, ACT_THEHIVE_TASK),
        branch("br_hive_cortex_hash", ACT_THEHIVE, ACT_CORTEX_HASH),
        branch("br_hive_cortex_hash_virusshare", ACT_THEHIVE, ACT_CORTEX_HASH_VIRUSSHARE),
        branch("br_hive_cortex_ip", ACT_THEHIVE, ACT_CORTEX_IP),
        branch("br_hive_cortex_ip_dshield", ACT_THEHIVE, ACT_CORTEX_IP_DSHIELD),
        branch("br_hive_cortex_ip_mnemonic_pdns", ACT_THEHIVE, ACT_CORTEX_IP_MNEMONIC_PDNS),
        branch("br_hive_cortex_ip_googledns", ACT_THEHIVE, ACT_CORTEX_IP_GOOGLEDNS),
        branch("br_hive_cortex_ip_ipapi", ACT_THEHIVE, ACT_CORTEX_IP_IPAPI),
        branch("br_hive_misp_create", ACT_THEHIVE, ACT_MISP_CREATE),
        branch("br_misp_create_search", ACT_MISP_CREATE, ACT_MISP),
        branch("br_hive_build_es", ACT_THEHIVE, ACT_BUILD_ES_JSON),
        # Case created → advanced analysis
        branch("br_hive_tenzir", ACT_THEHIVE, ACT_TENZIR_ANALYZE),
        branch("br_tenzir_create_serve", ACT_TENZIR_ANALYZE, ACT_TENZIR_SERVE),
        branch("br_hive_network", ACT_THEHIVE, ACT_NETWORK_WATCH),
        branch("br_hive_redis", ACT_THEHIVE, ACT_REDIS_CACHE),
        branch("br_hive_loki", ACT_THEHIVE, ACT_LOKI_SEARCH),
        # Cortex hash → verify job
        branch("br_cortex_hash_verify", ACT_CORTEX_HASH, ACT_VERIFY_CORTEX_HASH),
        # Cortex IP → verify job
        branch("br_cortex_ip_verify", ACT_CORTEX_IP, ACT_VERIFY_CORTEX_IP),
        # MISP → verify search
        branch("br_misp_verify", ACT_MISP, ACT_VERIFY_MISP),
        # build_es_json → ES
        branch("br_build_es", ACT_BUILD_ES_JSON, ACT_ES),
        # ES → verify indexing
        branch("br_es_verify", ACT_ES, ACT_VERIFY_ES),
        # New analysis → verification
        branch("br_tenzir_verify", ACT_TENZIR_SERVE, ACT_VERIFY_TENZIR),
        branch("br_network_verify", ACT_NETWORK_WATCH, ACT_VERIFY_NETWORK),
        branch("br_redis_verify", ACT_REDIS_CACHE, ACT_VERIFY_REDIS),
        branch("br_loki_verify", ACT_LOKI_SEARCH, ACT_VERIFY_LOKI),
        # Verifications → calculate decision (N6)
        branch("br_obs_hash_verify", ACT_THEHIVE_OBS_HASH, ACT_VERIFY_OBS_HASH),
        branch("br_verify_obs_hash_decision", ACT_VERIFY_OBS_HASH, ACT_CALC_DECISION),
        branch("br_obs_ip_verify", ACT_THEHIVE_OBS_IP, ACT_VERIFY_OBS_IP),
        branch("br_verify_obs_ip_decision", ACT_VERIFY_OBS_IP, ACT_CALC_DECISION),
        branch("br_task_verify", ACT_THEHIVE_TASK, ACT_VERIFY_TASK),
        branch("br_verify_task_decision", ACT_VERIFY_TASK, ACT_CALC_DECISION),
        branch("br_verify_hash_decision", ACT_VERIFY_CORTEX_HASH, ACT_CALC_DECISION),
        branch("br_verify_ip_decision", ACT_VERIFY_CORTEX_IP, ACT_CALC_DECISION),
        branch("br_verify_misp_decision", ACT_VERIFY_MISP, ACT_CALC_DECISION),
        branch("br_verify_es_decision", ACT_VERIFY_ES, ACT_CALC_DECISION),
        # New analysis → calculate decision
        branch("br_verify_tenzir_decision", ACT_VERIFY_TENZIR, ACT_CALC_DECISION),
        branch("br_verify_network_decision", ACT_VERIFY_NETWORK, ACT_CALC_DECISION),
        branch("br_verify_redis_decision", ACT_VERIFY_REDIS, ACT_CALC_DECISION),
        branch("br_verify_loki_decision", ACT_VERIFY_LOKI, ACT_CALC_DECISION),
        # New Cortex analyzers → calculate decision (no individual verification)
        branch("br_cortex_hash_virusshare_decision", ACT_CORTEX_HASH_VIRUSSHARE, ACT_CALC_DECISION),
        branch("br_cortex_ip_dshield_decision", ACT_CORTEX_IP_DSHIELD, ACT_CALC_DECISION),
        branch(
            "br_cortex_ip_mnemonic_pdns_decision", ACT_CORTEX_IP_MNEMONIC_PDNS, ACT_CALC_DECISION
        ),
        branch("br_cortex_ip_googledns_decision", ACT_CORTEX_IP_GOOGLEDNS, ACT_CALC_DECISION),
        branch("br_cortex_ip_ipapi_decision", ACT_CORTEX_IP_IPAPI, ACT_CALC_DECISION),
        # ── N6 decision → N7/N7b branching ──
        # NOTE: Shuffle 2.2.1's native branch conditions never evaluate as true.
        # Both branches are unconditional; each downstream node performs its
        # own internal guard against $calc_decision.message.decision.
        branch("br_decision_contain", ACT_CALC_DECISION, ACT_CONTAINMENT),
        branch("br_contain_inprogress", ACT_CONTAINMENT, ACT_UPDATE_INPROGRESS),
        branch("br_inprogress_notify", ACT_UPDATE_INPROGRESS, ACT_NOTIFY_CRITICAL),
        branch("br_notify_critical_mttr", ACT_NOTIFY_CRITICAL, ACT_CALC_MTTR),
        branch("br_decision_observe", ACT_CALC_DECISION, ACT_MARK_FP),
        branch("br_fp_notify_info", ACT_MARK_FP, ACT_NOTIFY_INFO),
        branch("br_notify_info_mttr", ACT_NOTIFY_INFO, ACT_CALC_MTTR),
        # Calculate MTTR → build summary → enrich case → build metrics → index metrics
        branch("br_mttr_summary", ACT_CALC_MTTR, ACT_BUILD_HIVE_SUMMARY),
        branch("br_summary_enrich", ACT_BUILD_HIVE_SUMMARY, ACT_ENRICH_CASE),
        branch("br_enrich_metrics_json", ACT_ENRICH_CASE, ACT_BUILD_METRICS_JSON),
        branch("br_metrics_json_index", ACT_BUILD_METRICS_JSON, ACT_INDEX_METRICS),
    ]

    branches_list = [
        b
        for b in branches_list
        if b["source_id"] not in _unavailable and b["destination_id"] not in _unavailable
    ]
    branches_list.extend(ctx.dynamic_cortex_branches)

    return branches_list
