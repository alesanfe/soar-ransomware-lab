# Embedded script: normalize_inputs
# Executed by Shuffle Tools (execute_python) as the first workflow node.
# Receives the FULL execution argument as a JSON string via $exec and
# parses it in Python. This avoids shuffle_variable_error when optional
# fields (process_name, confidence, user, file_path, mitre_tactics) are
# missing from the webhook payload.
#
# Subsequent nodes reference $normalize_inputs.message.<field> for optional
# fields and $exec.<field> for required fields.
"""Shuffle node: verify signature, validate contract, normalize alert fields.

CONTRACT-001/003 + HMAC-002 + INPUT-002 embedded mirror:
- Verifies the embedded ``security`` envelope signature (HMAC-SHA256)
  when ``ALERT_SIGNING_KEY`` is provisioned — unsigned payloads are
  rejected when a key exists; legacy unsigned mode only when the key
  is intentionally empty (lab transition, documented).
- Severity shares the canonical 0..4 table with the API — nothing the
  API admits can be dropped here on severity alone.
- src_ip/hostname are validated and emitted url-encoded (*_enc) so
  downstream nodes can interpolate them into URLs without injection.
- On rejection a best-effort signed callback reports the verdict to
  /api/v1/alerts/callback so admission state stays honest (CONTRACT-004).
"""

import hashlib
import hmac
import json
import logging
import re
import socket
import time

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

# ── Embedded provisioning (replaced at workflow setup) ────────────────────────
ALERT_SIGNING_KEY = "__ALERT_SIGNING_KEY__"
ALERT_KEY_ID = "__ALERT_KEY_ID__"
CALLBACK_TOKEN = "__CALLBACK_TOKEN__"
CALLBACK_HMAC_KEY = "__CALLBACK_HMAC_KEY__"
CALLBACK_KEY_ID = "__CALLBACK_KEY_ID__"
API_CALLBACK_URL = "http://api:8000/api/v1/alerts/callback"
if ALERT_SIGNING_KEY.startswith("__"):
    ALERT_SIGNING_KEY = ""
if CALLBACK_TOKEN.startswith("__"):
    CALLBACK_TOKEN = ""
if CALLBACK_HMAC_KEY.startswith("__"):
    CALLBACK_HMAC_KEY = ""


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()


def _verify_envelope(msg):
    """HMAC-002: verify the embedded security block (mirror of
    soar_lab.security.webhook_signing.verify_envelope)."""
    sec = msg.get("security")
    if not isinstance(sec, dict):
        if ALERT_SIGNING_KEY:
            return "missing security envelope"
        return None  # unsigned mode (key not provisioned)
    if ALERT_SIGNING_KEY and sec.get("key_id") not in (ALERT_KEY_ID, None):
        return "unknown key id"
    if not ALERT_SIGNING_KEY:
        return None  # envelope present but no key to check — accept (lab)
    if sec.get("alg") != "v1":
        return "envelope alg not allowed"
    try:
        if abs(time.time() - int(sec.get("timestamp"))) > 300:
            return "envelope timestamp stale"
    except (TypeError, ValueError):
        return "envelope timestamp malformed"
    clean = {k: v for k, v in msg.items() if k != "security"}
    digest = hashlib.sha256(_canonical(clean)).hexdigest()
    if not hmac.compare_digest(digest, str(sec.get("payload_sha256", ""))):
        return "payload digest mismatch"
    expected = hmac.new(
        ALERT_SIGNING_KEY.encode(),
        "v1|%s|%s|%s" % (int(sec["timestamp"]), sec.get("nonce"), digest).encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, str(sec.get("signature", ""))):
        return "envelope signature mismatch"
    return None


def _send_callback(admission_id, outcome, reason):
    """CONTRACT-004: best-effort signed verdict back to the API."""
    if not admission_id or not CALLBACK_TOKEN:
        return
    import urllib.request
    body = json.dumps({
        "admission_id": admission_id,
        "outcome": outcome,
        "reason": reason[:200],
    }).encode()
    headers = {"Content-Type": "application/json", "X-Service-Token": CALLBACK_TOKEN}
    if CALLBACK_HMAC_KEY:
        nonce = hashlib.sha256(("%s%s" % (time.time(), admission_id)).encode()).hexdigest()[:32]
        ts = str(int(time.time()))
        csha = hashlib.sha256(body).hexdigest()
        canonical = "POST\n/api/v1/alerts/callback\n%s\n%s\n%s" % (ts, nonce, csha)
        sig = hmac.new(CALLBACK_HMAC_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        headers.update({
            "X-SOAR-Signature-Version": "v1",
            "X-SOAR-Key-Id": CALLBACK_KEY_ID,
            "X-SOAR-Timestamp": ts,
            "X-SOAR-Nonce": nonce,
            "X-SOAR-Content-SHA256": csha,
            "X-SOAR-Signature": "v1=" + sig,
        })
    try:
        req = urllib.request.Request(API_CALLBACK_URL, data=body, headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # verdict loss is logged by the API side via stuck admissions


def _reject(reason):
    _send_callback(exec_data.get("admission_id"), "rejected", reason)
    raise KeyboardInterrupt("REJECTED: %s" % reason)


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

for _h in _dns_hosts:
    for _attempt in range(5):
        try:
            socket.getaddrinfo(_h, None)
            break
        except Exception:
            time.sleep(1)

# ── Signature verification (before any field is trusted) ──────────────────────
_sig_err = _verify_envelope(exec_data)
if _sig_err:
    _reject("signature: %s" % _sig_err)

# CONTRACT-003: envelope unwrapping + version check. When the forwarder
# wraps the alert it still copies fields top-level, so exec_data works
# for both legacy flat payloads and enveloped ones.
_schema_version = str(exec_data.get("schema_version", "1.0"))
if _schema_version not in ("1.0",):
    _reject("unknown schema_version %s" % _schema_version)

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


# ── CONTRACT-001: canonical severity — same table as the API ─────────────────
_SEV_NAMES = {
    "informational": 0, "info": 0,
    "low": 1,
    "medium": 2, "med": 2, "warning": 2, "warn": 2,
    "high": 3,
    "critical": 4, "crit": 4,
}
_sev_raw = exec_data.get("severity", None)
if _sev_raw is None:
    _reject("missing webhook severity")
if isinstance(_sev_raw, bool):
    _reject("severity must not be a bool")
if isinstance(_sev_raw, (int, float)):
    severity = int(_sev_raw)
    if not (float(_sev_raw) == severity) or severity < 0 or severity > 4:
        _reject("severity out of range: %s" % _sev_raw)
else:
    _txt = str(_sev_raw).strip().lower()
    if _txt in _SEV_NAMES:
        severity = _SEV_NAMES[_txt]
    elif re.fullmatch(r"\d+(?:\.0+)?", _txt):
        severity = int(float(_txt))
        if severity < 0 or severity > 4:
            _reject("severity out of range: %s" % _sev_raw)
    else:
        _reject("unknown severity: %s" % _sev_raw)

# ── INPUT-002: validate + url-encode fields used inside downstream URLs ──────
import ipaddress
from urllib.parse import quote

_src_ip = str(_get_field("src_ip") or "")
src_ip_enc = ""
if _src_ip:
    try:
        ipaddress.ip_address(_src_ip)
        src_ip_enc = quote(_src_ip, safe="")
    except ValueError:
        _reject("invalid src_ip")

_hostname = str(_get_field("hostname") or "")
_HOST_RE = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9_.-]*[A-Za-z0-9])?$")
hostname_enc = ""
if _hostname:
    if not _HOST_RE.match(_hostname):
        _reject("invalid hostname")
    hostname_enc = quote(_hostname, safe="")

# Build normalized output with defaults for optional fields
normalized = {
    "severity": severity,
    "thehive_severity": min(3, max(1, severity)),  # TheHive scale 1..3
    "alert_id": _get_field("alert_id"),
    "admission_id": exec_data.get("admission_id", ""),
    "event_id": exec_data.get("event_id", ""),
    "delivery_id": exec_data.get("delivery_id", ""),
    "trace_id": exec_data.get("trace_id", ""),
    "alert_type": _get_field("alert_type", "ransomware"),
    "hostname": _hostname,
    "hostname_enc": hostname_enc,
    "src_ip": _src_ip,
    "src_ip_enc": src_ip_enc,
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

# Build the TheHive case JSON inline (fused from build_case_json — removes
# one ~3s sequential dispatch hop on the workflow critical path).
mitre_raw = str(normalized.get("mitre_techniques", ""))
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
hostname = normalized.get("hostname") or exec_data.get("hostname", "")
alert_id = normalized.get("alert_id") or exec_data.get("alert_id", "")
trace_id = normalized.get("trace_id") or exec_data.get("trace_id", "")
if not isinstance(trace_id, str) or trace_id.startswith("$"):
    trace_id = ""
hash_val = normalized.get("hash") or exec_data.get("hash", "")
src_ip = normalized.get("src_ip") or exec_data.get("src_ip", "")
alert_type = normalized.get("alert_type") or exec_data.get("alert_type", "")
if not alert_type or str(alert_type).startswith("$"):
    alert_type = "ransomware"
alert_type_str = str(alert_type).replace("_", " ").title()
normalized["case"] = {
    "title": f"{alert_type_str}: {hostname} - {alert_id} | MITRE: {mitre_str}",
    "description": (
        f"Alert: {alert_id} | Trace: {trace_id} | Type: {alert_type} | Host: {hostname}"
        f" | Hash: {hash_val} | IP: {src_ip} | MITRE: {mitre_str}"
    ),
    "severity": normalized["thehive_severity"],
    "tlp": 2,
    "tags": [
        "ransomware",
        "soar-lab",
        "automated",
        alert_type,
        f"alert_id:{alert_id}",
    ]
    + ([f"trace_id:{trace_id}"] if trace_id else [])
    + (
        ["priority:critical", "urgent"]
        if severity >= 3
        else (["priority:high"] if severity == 2 else [])
    ),
}

# CONTRACT-004: report acceptance so the admission reaches a real
# terminal state instead of staying "forwarded" forever.
_send_callback(exec_data.get("admission_id"), "accepted", "normalized")
print(json.dumps(normalized))
