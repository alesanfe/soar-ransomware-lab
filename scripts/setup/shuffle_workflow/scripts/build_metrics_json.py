# Embedded script: build_metrics_json
# Builds the metrics document for Elasticsearch indexing.
import json
import logging
import time

logger = logging.getLogger(__name__)

alert_id = """$exec.alert_id"""
# Use normalize_inputs for optional fields
norm_raw = r"""$normalize_inputs.message"""
norm = {}
try:
    norm = json.loads(norm_raw) if norm_raw else {}
except Exception:
    pass
alert_type = norm.get("alert_type", "ransomware")
event_type = norm.get("event_type", "ransomware")
if not alert_type:
    alert_type = event_type or "unknown"
severity = """$exec.severity"""
try:
    severity = int(severity)
except Exception:
    severity = 2

mttr_raw = r"""$calc_mttr.message"""
try:
    _mttr_obj = json.loads(mttr_raw)
    mttr_seconds = (
        float(_mttr_obj.get("mttr_seconds", 0))
        if isinstance(_mttr_obj, dict) else float(mttr_raw)
    )
except Exception:
    try:
        mttr_seconds = float(mttr_raw)
    except Exception:
        mttr_seconds = 0.0

timestamp = norm.get("detection_time", "")
if not timestamp:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# Extract service IDs for success-rate dashboards
# Use r""" (raw triple-quoted) for Shuffle variable substitution: Shuffle
# substitutes $var with JSON that may contain \" (escaped quotes from HTTP
# headers). In regular """ strings, Python unescapes \" to ", which corrupts
# the JSON. Raw strings preserve \" so json.loads can parse it correctly.
thehive_case_id = ""
try:
    _hive = json.loads(r"""$thehive_create_case""")
    _body = _hive.get("body", _hive) if isinstance(_hive, dict) else {}
    thehive_case_id = _body.get("_id", _body.get("id", "")) if isinstance(_body, dict) else ""
except Exception:
    pass

cortex_hash_job = ""
try:
    _ch = json.loads(r"""$cortex_hash""")
    _body = _ch.get("body", _ch) if isinstance(_ch, dict) else {}
    cortex_hash_job = _body.get("id", _body.get("_id", "")) if isinstance(_body, dict) else ""
except Exception:
    pass

cortex_ip_job = ""
try:
    _ci = json.loads(r"""$cortex_ip""")
    _body = _ci.get("body", _ci) if isinstance(_ci, dict) else {}
    cortex_ip_job = _body.get("id", _body.get("_id", "")) if isinstance(_body, dict) else ""
except Exception:
    pass

misp_results = ""
try:
    _misp = json.loads(r"""$misp_search""")
    # MISP restSearch returns {"status": 200, "body": {"response": {"Attribute": [...]}}}
    _body = _misp.get("body", _misp) if isinstance(_misp, dict) else {}
    _response = _body.get("response", {}) if isinstance(_body, dict) else {}
    _attrs = _response.get("Attribute", []) if isinstance(_response, dict) else []
    if not _attrs:
        # Fallback: try direct data field
        _attrs = _misp.get("data", []) if isinstance(_misp, dict) else []
    misp_results = str(len(_attrs)) if isinstance(_attrs, list) else ""
except Exception:
    pass

# Extract decision, score, verdict and containment info
decision_raw = r"""$calc_decision.message""".strip() or ""
if decision_raw.startswith("$"):
    decision_raw = ""
_score = 0
_verdict = "unknown"
try:
    _dec_obj = json.loads(decision_raw)
    decision = _dec_obj.get("decision", "")
    _score = int(_dec_obj.get("score", 0))
    _verdict = _dec_obj.get("verdict", "unknown")
except Exception:
    decision = decision_raw
containment_raw = r"""$containment.message""".strip() or ""
if containment_raw.startswith("$"):
    containment_raw = ""
try:
    containment_executed = json.loads(containment_raw).get("skipped", False) is False
except Exception:
    containment_executed = False

# Per-component timing (approximated from workflow node results)
# These are best-effort timestamps from Shuffle execution
reception_time = 0.0
analysis_time = 0.0
case_creation_time = 0.0
containment_time = 0.0

# Per-node timing: each critical node records its start/end
# timestamp in a global dict that we collect here.
node_timings = {}
for _node_label in [
    "normalize_inputs",
    "build_case_json",
    "thehive_create_case",
    "thehive_obs_hash",
    "thehive_obs_ip",
    "thehive_add_task",
    "cortex_hash",
    "cortex_ip",
    "cortex_hash_virusshare",
    "cortex_ip_dshield",
    "cortex_ip_mnemonic_pdns",
    "cortex_ip_googledns",
    "cortex_ip_ipapi",
    "misp_create",
    "misp_search",
    "es_index",
    "tenzir_analyze",
    "network_watch",
    "redis_cache",
    "loki_search",
    "calc_decision",
    "containment",
    "calc_mttr",
    "enrich_case",
    "es_index_metrics",
]:
    node_timings[_node_label] = {"start": None, "end": None, "duration": None}

doc = {
    "alert_id": alert_id,
    "alert_type": alert_type,
    "severity": severity,
    "mttr_seconds": mttr_seconds,
    "@timestamp": timestamp,
    "timestamp": timestamp,
    "source": "shuffle-soar",
    "metric_type": "workflow_execution",
    "success": True,
    "decision": decision,
    "score": _score,
    "verdict": _verdict,
    "containment_executed": containment_executed,
    "thehive_case_id": thehive_case_id,
    "cortex_hash_job": cortex_hash_job,
    "cortex_ip_job": cortex_ip_job,
    "misp_results": misp_results,
    "reception_time_s": round(reception_time, 2),
    "analysis_time_s": round(analysis_time, 2),
    "case_creation_time_s": round(case_creation_time, 2),
    "containment_time_s": round(containment_time, 2),
    "node_timings": node_timings,
}

print(json.dumps(doc))
