# Embedded script: build_es_json
# Builds the Elasticsearch document from all available data.
import json
import logging

logger = logging.getLogger(__name__)
mitre_raw = ""
try:
    _norm2 = json.loads(r"""$normalize_inputs.message""")
    _mt = _norm2.get("mitre_techniques", "")
    if isinstance(_mt, list):
        mitre_raw = json.dumps(_mt)
    elif isinstance(_mt, str):
        mitre_raw = _mt
    else:
        mitre_raw = ""
except Exception:
    _norm2 = {}
alert_id = _norm2.get("alert_id", "") or """$exec.alert_id"""
hostname = _norm2.get("hostname", "") or """$exec.hostname"""
src_ip = _norm2.get("src_ip", "") or """$exec.src_ip"""
hash_val = _norm2.get("hash", "") or """$exec.hash"""
# Handle mitre_techniques (can be array or string)
try:
    mitre_techniques = json.loads(mitre_raw)
except Exception:
    mitre_techniques = mitre_raw if mitre_raw else []
if isinstance(mitre_techniques, str):
    try:
        mitre_techniques = json.loads(mitre_techniques)
    except Exception:
        mitre_techniques = [mitre_techniques] if mitre_techniques else []
import time

severity_raw = """$exec.severity"""
try:
    severity = int(float(severity_raw))
except Exception:
    severity = 2
if severity < 1 or severity > 3:
    severity = 2
timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
# Use normalize_inputs for optional/semi-optional fields
norm_raw = r"""$normalize_inputs.message"""
norm = {}
try:
    norm = json.loads(norm_raw) if norm_raw else {}
except Exception:
    pass
alert_type = norm.get("alert_type", "ransomware")
source = norm.get("source", "shuffle-soar")
detection_time = norm.get("detection_time", "")
event_type = norm.get("event_type", "ransomware")
process_name = norm.get("process_name", "")
confidence_raw = str(norm.get("confidence", ""))
user_name = norm.get("user", "")
file_path = norm.get("file_path", "")
mitre_tactics = norm.get("mitre_tactics", "")


# Normalize: convert non-string scalars/lists to safe strings
def _to_str(v):
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple)):
        try:
            return json.dumps(v)
        except Exception:
            return str(v)
    if v is None:
        return ""
    return str(v)


alert_type = _to_str(alert_type)
source = _to_str(source)
detection_time = _to_str(detection_time)
event_type = _to_str(event_type)
process_name = _to_str(process_name)
user_name = _to_str(user_name)
file_path = _to_str(file_path)
mitre_tactics = _to_str(mitre_tactics)
doc = {
    "alert_id": alert_id,
    "alert_type": alert_type,
    "hostname": hostname,
    "src_ip": src_ip,
    "hash": hash_val,
    "severity": severity,
    "mitre_techniques": mitre_techniques,
    "source": source,
    "workflow": "SOAR-Ransomware-Response",
    "status": "processed",
    "@timestamp": timestamp,
    "timestamp": timestamp,
}
if detection_time:
    doc["detection_time"] = detection_time
else:
    doc["detection_time"] = timestamp
if event_type and isinstance(event_type, str):
    doc["event_type"] = event_type
if process_name and isinstance(process_name, str) and not process_name.startswith("$"):
    doc["process_name"] = process_name
if confidence_raw and isinstance(confidence_raw, str) and not confidence_raw.startswith("$"):
    try:
        doc["confidence"] = int(float(confidence_raw))
    except Exception:
        pass
if user_name and isinstance(user_name, str) and not user_name.startswith("$"):
    doc["user"] = user_name
if file_path and isinstance(file_path, str) and not file_path.startswith("$"):
    # Redact sensitive path components (e.g. .ssh, id_rsa, .aws, .gnupg)
    # before indexing to prevent leaking private key paths in ES.
    _sensitive_patterns = [".ssh", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
                           ".aws", "credentials", ".gnupg", ".kube", ".docker"]
    _redacted = file_path
    for _pat in _sensitive_patterns:
        if _pat in _redacted.lower():
            _redacted = "REDACTED"
            break
    doc["file_path"] = _redacted
if mitre_tactics and isinstance(mitre_tactics, str) and not mitre_tactics.startswith("$"):
    try:
        doc["mitre_tactics"] = json.loads(mitre_tactics)
    except Exception:
        if isinstance(mitre_tactics, str) and mitre_tactics:
            doc["mitre_tactics"] = [mitre_tactics]
elif isinstance(mitre_tactics, list):
    doc["mitre_tactics"] = mitre_tactics

# Domain and URL fields (from C2 infrastructure in simulated alerts)
domain_val = norm.get("domain", "")
if isinstance(domain_val, str) and domain_val and not domain_val.startswith("$"):
    doc["domain"] = domain_val
url_val = norm.get("url", "")
if isinstance(url_val, str) and url_val and not url_val.startswith("$"):
    doc["url"] = url_val

# Multi-IoC fields (from TC-33 infostealer/forensics payloads)
_ioc_list_fields = [
    "all_hashes", "all_urls", "all_domains", "all_ips",
    "telegram_bot_id", "telegram_chat_id",
    "actor_github", "actor_telegram",
    "malware_type", "malware_family",
]
for _f in _ioc_list_fields:
    _v = norm.get(_f, "")
    if isinstance(_v, list):
        doc[_f] = _v
    elif isinstance(_v, str) and _v and not _v.startswith("$"):
        doc[_f] = _v

# iocs_count (integer)
_iocs_count = norm.get("iocs_count", "")
if isinstance(_iocs_count, int):
    doc["iocs_count"] = _iocs_count
elif isinstance(_iocs_count, str) and _iocs_count and not _iocs_count.startswith("$"):
    try:
        doc["iocs_count"] = int(_iocs_count)
    except Exception:
        pass

print(json.dumps(doc))
