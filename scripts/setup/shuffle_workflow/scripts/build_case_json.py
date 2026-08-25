# Embedded script: build_case_json
# Builds the TheHive case JSON from normalized inputs.
import json
import logging

logger = logging.getLogger(__name__)

norm_raw = r"""$normalize_inputs.message"""
try:
    _norm = json.loads(norm_raw)
except Exception:
    _norm = {}
severity_raw = str(_norm.get("severity", ""))
try:
    severity = int(float(severity_raw.strip()))
except Exception:
    severity = 2
if severity < 1 or severity > 3:
    severity = 2
mitre_raw = str(_norm.get("mitre_techniques", ""))
mitre_list = []
try:
    mitre_list = json.loads(mitre_raw)
    if not isinstance(mitre_list, list):
        mitre_list = [mitre_list]
except Exception:
    try:
        import ast

        mitre_list = ast.literal_eval(mitre_raw)
        if not isinstance(mitre_list, list):
            mitre_list = [mitre_list]
    except Exception:
        pass
if not mitre_list:
    mitre_list = [x.strip() for x in mitre_raw.strip("[]").split(",") if x.strip()]
mitre_str = ", ".join(str(m) for m in mitre_list) if mitre_list else "N/A"
hostname = _norm.get("hostname", "") or """$exec.hostname"""
alert_id = _norm.get("alert_id", "") or """$exec.alert_id"""
hash_val = _norm.get("hash", "") or """$exec.hash"""
src_ip = _norm.get("src_ip", "") or """$exec.src_ip"""
alert_type = _norm.get("alert_type", "") or """$exec.alert_type"""
# Normalize alert_type for title/tags
if not alert_type or alert_type.startswith("$"):
    alert_type = "ransomware"
alert_type_str = alert_type.replace("_", " ").title()
case = {
    "title": f"{alert_type_str}: {hostname} - {alert_id} | MITRE: {mitre_str}",
    "description": (
        f"Alert: {alert_id} | Type: {alert_type} | Host: {hostname} | Hash: {hash_val}"
        f" | IP: {src_ip} | MITRE: {mitre_str}"
    ),
    "severity": severity,
    "tlp": 2,
    "tags": ["ransomware", "soar-lab", "automated", alert_type, f"alert_id:{alert_id}"]
    + (
        ["priority:critical", "urgent"]
        if severity >= 3
        else (["priority:high"] if severity == 2 else [])
    ),
}
print(json.dumps(case))
