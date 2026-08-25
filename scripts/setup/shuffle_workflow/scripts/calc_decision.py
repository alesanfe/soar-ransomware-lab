# Embedded script: calc_decision
# Calculate score and verdict from ALL available data sources:
# Cortex (hash + IP taxonomies), MISP (IoC count), severity, MITRE,
# Tenzir (network events), Network Watcher (connections), Loki (logs).
#
# Scoring model (0-100):
#   - Cortex taxonomies: max(level value) across all analyzers
#   - MISP IoCs: +15 if matches found
#   - Webhook confidence: base score
#   - Severity: 1→20, 2→40, 3→60
#   - Alert type: ransomware +25, malware/phishing/intrusion +15
#   - MITRE high-risk techniques: +10 per matched technique
#   - Tenzir: +5-25 based on suspicious network patterns
#   - Network Watcher: +5-20 based on suspicious connections
#   - Loki: +10-30 based on ransomware indicator patterns
#
# Verdict: malicious | suspicious | safe | unknown
# Decision: contain (score>=80 or malicious) | observe
import ast
import json
import logging

logger = logging.getLogger(__name__)


def _parse(raw):
    raw = raw.strip() if raw else ""
    if not raw or raw.startswith("$"):
        return None
    try:
        return json.loads(raw)
    except Exception:
        try:
            return ast.literal_eval(raw)
        except Exception:
            return None


def _parse_cortex_taxonomies(result):
    """Extract score and verdict from Cortex analyzer taxonomies.

    Cortex taxonomies have: level (info/safe/suspicious/malicious),
    namespace (analyzer name), predicate (service), value (score).
    """
    score = 0
    verdict = "unknown"
    taxonomies = []
    if not result or not isinstance(result, dict):
        return score, verdict, taxonomies
    body = result.get("body", result)
    if not isinstance(body, dict):
        return score, verdict, taxonomies
    if body.get("status", "") != "Success":
        return score, verdict, taxonomies
    report = body.get("report", {})
    if not isinstance(report, dict):
        return score, verdict, taxonomies
    taxonomies = report.get("summary", {}).get("taxonomies", [])
    for t in taxonomies:
        level = t.get("level", "")
        val = t.get("value", 0)
        try:
            val = int(float(str(val).replace("%", "")))
        except Exception:
            val = 0
        score = max(score, val)
        if level == "malicious":
            verdict = "malicious"
        elif level == "suspicious" and verdict != "malicious":
            verdict = "suspicious"
    return score, verdict, taxonomies


# ── High-risk MITRE techniques for ransomware ──────────────────────────────
HIGH_RISK_TECHNIQUES = {
    "T1486": "Data Encrypted for Impact",
    "T1485": "Data Destroyed",
    "T1490": "Inhibit System Recovery",
    "T1059": "Command and Scripting Interpreter",
    "T1218": "System Binary Proxy Execution",
    "T1071": "Application Layer Protocol",
    "T1571": "Non-Standard Port",
    "T1572": "Protocol Tunneling",
    "T1573": "Encrypted Channel",
}

# ── Ransomware indicator patterns for Loki log analysis ────────────────────
RANSOMWARE_LOG_PATTERNS = [
    "vssadmin",
    "delete shadows",
    "shadowcopy",
    "shadow copy",
    "wbadmin",
    "delete catalog",
    "bcdedit",
    "recoveryenabled",
    "bootstatuspolicy",
    "cipher",
    "fsutil",
    "usn",
    "deletejournal",
    "icacls",
    "grant Everyone",
    "taskkill",
    "net stop",
    "netsh",
    "advfirewall",
    "firewall set opmode",
    "DisableBehaviorMonitoring",
    "DisableOnAccessProtection",
    "DisableScanOnRealtimeEnable",
    "wevtutil",
    "clear-log",
    ".encrypted",
    ".locked",
    ".crypt",
    ".lock64",
    ".cuba",
    ".avos",
    ".play",
    ".blackbyte",
    ".revive",
    ".ransom",
    "Restore-My-Files",
    "HOW_TO_DECRYPT",
    "READ_ME",
]

# ── Suspicious network ports (C2, reverse shells, non-standard) ───────────
SUSPICIOUS_PORTS = {4444, 1337, 2083, 2087, 8088, 8443, 9999, 1234, 31337, 4445, 5555}

# ── Standard ports (not suspicious) ────────────────────────────────────────
STANDARD_PORTS = {80, 443, 53, 25, 22, 3389, 5985, 5986, 445, 139, 123}


# ── Derive score from all available data sources ──────────────────────────
score = 0
verdict = "unknown"
factors = []

# 1. Webhook confidence (if present, use as base score)
norm_raw = r"""$normalize_inputs.message"""
norm = {}
try:
    norm = json.loads(norm_raw) if norm_raw else {}
except Exception:
    pass
confidence_raw = str(norm.get("confidence", ""))
try:
    confidence = int(float(confidence_raw))
    if confidence > 0:
        score = max(score, confidence)
        factors.append(f"webhook.confidence={confidence}")
except Exception:
    pass

# 2. Severity from webhook (1=low, 2=medium, 3=high/critical)
# Use normalize_inputs severity (already mapped from string/int)
severity_raw = str(norm.get("severity", """$exec.severity"""))
try:
    severity = int(float(severity_raw))
    sev_score = {1: 20, 2: 40, 3: 60}.get(severity, 20)
    score = max(score, sev_score)
    factors.append(f"webhook.severity={severity}({sev_score})")
except Exception:
    pass

# 3. Alert type bonus (ransomware is critical threat)
alert_type = norm.get("alert_type", "ransomware")
if isinstance(alert_type, str):
    alert_type = alert_type.strip().lower()
else:
    alert_type = "ransomware"
if alert_type == "ransomware":
    score = min(100, score + 25)
    factors.append("alert_type.ransomware(+25)")
elif alert_type in ("malware", "phishing", "intrusion"):
    score = min(100, score + 15)
    factors.append(f"alert_type.{alert_type}(+15)")

# 4. MITRE techniques bonus (T1486 = encryption for impact, etc.)
_mitre_val = norm.get("mitre_techniques", "")
if isinstance(_mitre_val, list):
    mitre = _mitre_val
elif isinstance(_mitre_val, str) and _mitre_val:
    try:
        mitre = json.loads(_mitre_val)
    except Exception:
        try:
            import ast as _ast
            mitre = _ast.literal_eval(_mitre_val)
        except Exception:
            mitre = [_mitre_val]
else:
    mitre = []
if isinstance(mitre, str):
    try:
        mitre = json.loads(mitre)
    except Exception:
        mitre = [mitre] if mitre else []
if isinstance(mitre, list):
    matched = [t for t in mitre if t in HIGH_RISK_TECHNIQUES]
    if matched:
        score = min(100, score + len(matched) * 10)
        factors.append(f"mitre.high_risk={matched}(+{len(matched) * 10})")

# 5. Cortex analyzer results (hash + IP) — primary threat intelligence
cortex_hash_raw = r"""$cortex_hash"""
cortex_hash = _parse(cortex_hash_raw)
ch_score, ch_verdict, ch_taxonomies = _parse_cortex_taxonomies(cortex_hash)
if ch_score > 0:
    score = max(score, ch_score)
    factors.append(f"cortex.hash(score={ch_score},verdict={ch_verdict})")
if ch_verdict == "malicious":
    verdict = "malicious"
elif ch_verdict == "suspicious" and verdict != "malicious":
    verdict = "suspicious"
# Log individual taxonomy details
for t in ch_taxonomies:
    factors.append(
        f"cortex.hash.{t.get('namespace', '?')}.{t.get('predicate', '?')}"
        f"={t.get('level', '?')}({t.get('value', '?')})"
    )

cortex_ip_raw = r"""$cortex_ip"""
cortex_ip = _parse(cortex_ip_raw)
ci_score, ci_verdict, ci_taxonomies = _parse_cortex_taxonomies(cortex_ip)
if ci_score > 0:
    score = max(score, ci_score)
    factors.append(f"cortex.ip(score={ci_score},verdict={ci_verdict})")
if ci_verdict == "malicious":
    verdict = "malicious"
elif ci_verdict == "suspicious" and verdict != "malicious":
    verdict = "suspicious"
for t in ci_taxonomies:
    factors.append(
        f"cortex.ip.{t.get('namespace', '?')}.{t.get('predicate', '?')}"
        f"={t.get('level', '?')}({t.get('value', '?')})"
    )

# 5b. Additional Cortex IP analyzers (DShield, Mnemonic pDNS, GoogleDNS, IP-API)
for _node_var, _label in [
    (r"""$cortex_ip_dshield""", "dshield"),
    (r"""$cortex_ip_mnemonic_pdns""", "mnemonic_pdns"),
    (r"""$cortex_ip_googledns""", "googledns"),
    (r"""$cortex_ip_ipapi""", "ipapi"),
]:
    _raw = _node_var
    _result = _parse(_raw)
    _s, _v, _t = _parse_cortex_taxonomies(_result)
    if _s > 0:
        score = max(score, _s)
        factors.append(f"cortex.{_label}(score={_s},verdict={_v})")
    if _v == "malicious":
        verdict = "malicious"
    elif _v == "suspicious" and verdict != "malicious":
        verdict = "suspicious"
    for t in _t:
        factors.append(
            f"cortex.{_label}.{t.get('namespace', '?')}.{t.get('predicate', '?')}"
            f"={t.get('level', '?')}({t.get('value', '?')})"
        )

# 6. MISP threat intelligence — IoCs found
misp_raw = r"""$misp_search"""
misp = _parse(misp_raw)
misp_ioc_count = 0
misp_ioc_types = []
if misp and isinstance(misp, dict):
    body = misp.get("body", misp)
    resp = body.get("response", body.get("data", {})) if isinstance(body, dict) else {}
    if isinstance(resp, dict):
        attrs = resp.get("Attribute", [])
    elif isinstance(resp, list):
        attrs = resp
    else:
        attrs = []
    if isinstance(attrs, list) and len(attrs) > 0:
        misp_ioc_count = len(attrs)
        misp_ioc_types = list({a.get("type", "unknown") for a in attrs if isinstance(a, dict)})
        score = min(100, score + 15)
        factors.append(f"misp.iocs={misp_ioc_count}(+15)")
        if verdict == "unknown":
            verdict = "suspicious"

# 7. Event type bonus
event_type = norm.get("event_type", "ransomware")
if isinstance(event_type, str):
    event_type = event_type.strip().lower()
else:
    event_type = "ransomware"
if "ransomware" in event_type:
    score = min(100, score + 10)
    factors.append("event_type.ransomware(+10)")

# ── 8. Tenzir network analysis — suspicious network patterns ──────────────
tenzir_raw = r"""$tenzir_serve"""
tenzir = _parse(tenzir_raw)
tenzir_events = []
tenzir_suspicious = 0
if tenzir and isinstance(tenzir, dict):
    events = tenzir.get("events", tenzir.get("body", {}).get("events", []))
    if isinstance(events, list):
        tenzir_events = events
        for evt in events:
            if not isinstance(evt, dict):
                continue
            # Check for suspicious destination ports
            dst_port = evt.get("dst_port") or evt.get("destination_port")
            if dst_port and int(dst_port) in SUSPICIOUS_PORTS:
                tenzir_suspicious += 1
                factors.append(f"tenzir.suspicious_port={dst_port}")
            # Check for connections to external IPs (non-RFC1918)
            dst_ip = evt.get("dst_ip") or evt.get("destination_ip", "")
            if dst_ip and not dst_ip.startswith(
                (
                    "10.",
                    "172.16.",
                    "172.17.",
                    "172.18.",
                    "172.19.",
                    "172.20.",
                    "172.21.",
                    "172.22.",
                    "172.23.",
                    "172.24.",
                    "172.25.",
                    "172.26.",
                    "172.27.",
                    "172.28.",
                    "172.29.",
                    "172.30.",
                    "172.31.",
                    "192.168.",
                    "127.",
                    "169.254.",
                )
            ):
                tenzir_suspicious += 1
                factors.append(f"tenzir.external_ip={dst_ip}")
            # Check for DNS queries to suspicious TLDs
            query = evt.get("query", "") or evt.get("dns_query", "")
            if query and any(
                query.endswith(tld)
                for tld in (".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".click", ".loan")
            ):
                tenzir_suspicious += 1
                factors.append(f"tenzir.suspicious_tld={query}")
        if tenzir_suspicious > 0:
            tenzir_bonus = min(25, tenzir_suspicious * 5)
            score = min(100, score + tenzir_bonus)
            factors.append(f"tenzir.suspicious_events={tenzir_suspicious}(+{tenzir_bonus})")
            if verdict == "unknown":
                verdict = "suspicious"
        elif len(tenzir_events) > 0:
            factors.append(f"tenzir.events={len(tenzir_events)}(no suspicious)")

# ── 9. Network Watcher — suspicious connections ───────────────────────────
network_raw = r"""$network_watch"""
network = _parse(network_raw)
network_suspicious = 0
network_connections = []
if network and isinstance(network, dict):
    connections = network.get("connections", network.get("body", {}).get("connections", []))
    if isinstance(connections, list):
        network_connections = connections
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            port = conn.get("dst_port") or conn.get("remote_port") or conn.get("port")
            if port and int(port) in SUSPICIOUS_PORTS:
                network_suspicious += 1
                factors.append(f"network.suspicious_port={port}")
            # Check connection state (ESTABLISHED to external = suspicious)
            state = conn.get("state", "").upper()
            dst_ip = conn.get("dst_ip") or conn.get("remote_ip", "")
            if (
                state == "ESTABLISHED"
                and dst_ip
                and not dst_ip.startswith(
                    (
                        "10.",
                        "172.16.",
                        "172.17.",
                        "172.18.",
                        "172.19.",
                        "172.20.",
                        "172.21.",
                        "172.22.",
                        "172.23.",
                        "172.24.",
                        "172.25.",
                        "172.26.",
                        "172.27.",
                        "172.28.",
                        "172.29.",
                        "172.30.",
                        "172.31.",
                        "192.168.",
                        "127.",
                        "169.254.",
                    )
                )
            ):
                network_suspicious += 1
                factors.append(f"network.external_connection={dst_ip}:{port}")
            # High connection count to same IP = potential beaconing
            count = conn.get("count", 0)
            if count and int(count) >= 15:
                network_suspicious += 1
                factors.append(f"network.beaconing={dst_ip}(count={count})")
        if network_suspicious > 0:
            network_bonus = min(20, network_suspicious * 5)
            score = min(100, score + network_bonus)
            factors.append(f"network.suspicious={network_suspicious}(+{network_bonus})")
            if verdict == "unknown":
                verdict = "suspicious"
        elif len(network_connections) > 0:
            factors.append(f"network.connections={len(network_connections)}(no suspicious)")

# ── 10. Loki log analysis — ransomware indicator patterns ─────────────────
loki_raw = r"""$loki_search"""
loki = _parse(loki_raw)
loki_matches = 0
loki_patterns_found = []
if loki and isinstance(loki, dict):
    data = loki.get("data", {})
    if isinstance(data, dict):
        results = data.get("result", [])
    else:
        results = []
    if isinstance(results, list):
        for stream in results:
            if not isinstance(stream, dict):
                continue
            values = stream.get("values", [])
            if not isinstance(values, list):
                continue
            for entry in values:
                # Loki format: [timestamp, log_line]
                log_line = ""
                if isinstance(entry, list) and len(entry) >= 2:
                    log_line = str(entry[1]).lower()
                elif isinstance(entry, str):
                    log_line = entry.lower()
                for pattern in RANSOMWARE_LOG_PATTERNS:
                    if pattern.lower() in log_line:
                        loki_matches += 1
                        if pattern not in loki_patterns_found:
                            loki_patterns_found.append(pattern)
        if loki_matches > 0:
            # Critical patterns (shadow copy deletion, encryption) get higher weight
            critical_patterns = {
                "vssadmin",
                "delete shadows",
                "shadowcopy",
                "shadow copy",
                "wbadmin",
                "delete catalog",
                ".encrypted",
                ".locked",
                ".crypt",
                "Restore-My-Files",
                "HOW_TO_DECRYPT",
            }
            critical_count = sum(1 for p in loki_patterns_found if p in critical_patterns)
            loki_bonus = min(30, loki_matches * 3 + critical_count * 10)
            score = min(100, score + loki_bonus)
            factors.append(
                f"loki.matches={loki_matches},patterns={loki_patterns_found}(+{loki_bonus})"
            )
            if critical_count > 0:
                if verdict != "malicious":
                    verdict = "suspicious"
                factors.append(f"loki.critical_patterns={critical_count}")
        elif len(results) > 0:
            factors.append(f"loki.entries={len(results)}(no ransomware patterns)")

# ── Derive verdict from final score if still unknown ──────────────────────
if verdict == "unknown":
    if score >= 80:
        verdict = "malicious"
    elif score >= 50:
        verdict = "suspicious"
    elif score > 0:
        verdict = "safe"

# ── Decision: contain if score >= 80 or verdict == malicious ──────────────
if score >= 80 or verdict == "malicious":
    decision = "contain"
else:
    decision = "observe"

result = {
    "score": score,
    "verdict": verdict,
    "decision": decision,
    "factors": factors,
    "misp_ioc_count": misp_ioc_count,
    "misp_ioc_types": misp_ioc_types,
    "tenzir_events": len(tenzir_events),
    "tenzir_suspicious": tenzir_suspicious,
    "network_connections": len(network_connections),
    "network_suspicious": network_suspicious,
    "loki_matches": loki_matches,
    "loki_patterns": loki_patterns_found,
}
print(json.dumps(result))
