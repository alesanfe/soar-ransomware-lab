# Embedded script: normalize_inputs
# Executed by Shuffle Tools (execute_python) as the first workflow node.
# Receives the FULL execution argument as a JSON string via $exec and
# parses it in Python. This avoids shuffle_variable_error when optional
# fields (process_name, confidence, user, file_path, mitre_tactics) are
# missing from the webhook payload.
#
# Subsequent nodes reference $normalize_inputs.message.<field> for optional
# fields and $exec.<field> for required fields.
import json
import logging
import re
import socket

logger = logging.getLogger(__name__)

# $exec alone returns the full execution argument as a string
raw_exec = r"""$exec"""
exec_data = {}
try:
    exec_data = json.loads(raw_exec)
    if not isinstance(exec_data, dict):
        exec_data = {}
except Exception:
    pass

# DNS warmup: resolve all service hostnames to warm Docker's
# embedded DNS cache. This prevents intermittent
# NameResolutionError in subsequent http app nodes when
# Shuffle spins up a fresh worker container.
_dns_hosts = [
    "loki",
    "misp",
    "tenzir-node",
    "network-watcher",
    "api",
    "cortex",
    "thehive",
    "elasticsearch",
]
import time as _time

for _h in _dns_hosts:
    for _attempt in range(5):
        try:
            socket.getaddrinfo(_h, None)
            break
        except Exception:
            _time.sleep(1)

# Field aliases: map alternative field names from different simulators
# to the canonical names expected by the workflow.
_aliases = {
    "hash": ("file_hash", "filehash", "sha256", "md5"),
    "hostname": ("host", "hostname_fqdn", "endpoint"),
    "mitre_techniques": ("MITRE", "mitre", "mitre_technique", "techniques"),
    "detection_time": ("timestamp", "event_time", "detected_at"),
    "event_type": ("classification", "alert_type"),
    "alert_type": ("malware_type", "threat_type"),
}


def _get_field(key, default=""):
    """Get a field from exec_data, checking aliases."""
    val = exec_data.get(key, None)
    if val is not None:
        return val
    for alias in _aliases.get(key, ()):
        val = exec_data.get(alias, None)
        if val is not None:
            return val
    return default


# Validate severity (required) — accept both numeric (1-3) and string
# ("low", "medium", "high", "critical") formats.
severity_raw = str(exec_data.get("severity", "")).strip()
if not severity_raw:
    raise KeyboardInterrupt("REJECTED: missing webhook severity")
if re.match(r"^\d+(?:\.\d+)?$", severity_raw):
    severity = int(float(severity_raw))
else:
    _sev_map = {"low": 1, "medium": 2, "high": 3, "critical": 3, "info": 1, "warning": 2}
    severity = _sev_map.get(severity_raw.lower(), 0)
if severity < 1 or severity > 3:
    raise KeyboardInterrupt("REJECTED: severity out of range: %s" % severity_raw)

# Build normalized output with defaults for optional fields
normalized = {
    "severity": severity,
    "alert_id": _get_field("alert_id"),
    "alert_type": _get_field("alert_type", "ransomware"),
    "hostname": _get_field("hostname"),
    "src_ip": _get_field("src_ip"),
    "hash": _get_field("hash"),
    "source": _get_field("source", "shuffle-soar"),
    "detection_time": _get_field("detection_time"),
    "event_type": _get_field("event_type", _get_field("alert_type", "ransomware")),
    "mitre_techniques": _get_field("mitre_techniques"),
    "process_name": exec_data.get("process_name", ""),
    "confidence": exec_data.get("confidence", ""),
    "user": exec_data.get("user", ""),
    "file_path": exec_data.get("file_path", ""),
    "mitre_tactics": exec_data.get("mitre_tactics", ""),
    "domain": exec_data.get("domain", ""),
    "url": exec_data.get("url", ""),
    # Multi-IoC fields (TC-33 infostealer/forensics)
    "all_hashes": exec_data.get("all_hashes", ""),
    "all_urls": exec_data.get("all_urls", ""),
    "all_domains": exec_data.get("all_domains", ""),
    "all_ips": exec_data.get("all_ips", ""),
    "telegram_bot_id": exec_data.get("telegram_bot_id", ""),
    "telegram_chat_id": exec_data.get("telegram_chat_id", ""),
    "actor_github": exec_data.get("actor_github", ""),
    "actor_telegram": exec_data.get("actor_telegram", ""),
    "malware_type": exec_data.get("malware_type", ""),
    "malware_family": exec_data.get("malware_family", ""),
    "iocs_count": exec_data.get("iocs_count", ""),
}
print(json.dumps(normalized))
