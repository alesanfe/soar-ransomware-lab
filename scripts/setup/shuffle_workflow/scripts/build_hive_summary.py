# Embedded script: build_hive_summary
# Builds a comprehensive Markdown summary for TheHive case enrichment.
#
# Includes:
#   - Alert metadata (ID, host, IP, hash, MTTR)
#   - Cortex: full taxonomies (level, namespace, predicate, value) per analyzer
#   - MISP: individual IoCs with type and value
#   - Tenzir: network event details (src/dst IPs, ports, protocols)
#   - Network Watcher: connection details (dest IPs, ports, states)
#   - Loki: log entries with timestamps and matched ransomware patterns
#   - Redis: cache details
#   - Decision: score, verdict, decision, and contributing factors
import json
import logging

logger = logging.getLogger(__name__)

alert_id = """$exec.alert_id"""
hostname = """$exec.hostname"""
src_ip = """$exec.src_ip"""
hash_val = """$exec.hash"""
mttr_raw = r"""$calc_mttr.message"""
try:
    _mttr_obj = json.loads(mttr_raw)
    mttr = (
        str(_mttr_obj.get("mttr_seconds", mttr_raw))
        if isinstance(_mttr_obj, dict) else str(mttr_raw)
    )
except Exception:
    mttr = mttr_raw.strip() if mttr_raw else "N/A"


def _parse(raw):
    raw = raw.strip() if raw else ""
    if not raw or raw.startswith("$"):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _safe_str(v, max_len=200):
    """Safely convert any value to a truncated string."""
    if v is None:
        return "N/A"
    s = str(v)
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s


# ── Parse all analyzer results ─────────────────────────────────────────────
cortex_hash = _parse(r"""$cortex_hash""")
cortex_ip = _parse(r"""$cortex_ip""")
cortex_ip_dshield = _parse(r"""$cortex_ip_dshield""")
cortex_ip_mnemonic_pdns = _parse(r"""$cortex_ip_mnemonic_pdns""")
cortex_ip_googledns = _parse(r"""$cortex_ip_googledns""")
cortex_ip_ipapi = _parse(r"""$cortex_ip_ipapi""")
misp = _parse(r"""$misp_search""")
tenzir = _parse(r"""$tenzir_serve""")
network = _parse(r"""$network_watch""")
redis = _parse(r"""$redis_cache""")
loki = _parse(r"""$loki_search""")
decision_raw = r"""$calc_decision.message"""
decision_data = {}
try:
    decision_data = json.loads(decision_raw) if decision_raw else {}
except Exception:
    pass

# ── Build summary sections ─────────────────────────────────────────────────
parts = []

# ── Header ─────────────────────────────────────────────────────────────────
parts.append(f"# Ransomware Incident - {alert_id}")
parts.append("")
parts.append("| Field | Value |")
parts.append("|-------|-------|")
parts.append(f"| **Alert ID** | {alert_id} |")
parts.append(f"| **Hostname** | {hostname} |")
parts.append(f"| **Source IP** | {src_ip} |")
parts.append(f"| **File Hash** | `{hash_val}` |")
parts.append(f"| **MTTR** | {mttr} seconds |")

# Decision summary
score = decision_data.get("score", "N/A")
verdict = decision_data.get("verdict", "N/A")
decision = decision_data.get("decision", "N/A")
parts.append(f"| **Risk Score** | {score}/100 |")
parts.append(f"| **Verdict** | {verdict} |")
parts.append(f"| **Decision** | {decision} |")
parts.append("")

# ── Decision Factors ───────────────────────────────────────────────────────
factors = decision_data.get("factors", [])
if factors:
    parts.append("## Decision Factors")
    parts.append("")
    for f in factors:
        parts.append(f"- {f}")
    parts.append("")

# ── Cortex Analysis ────────────────────────────────────────────────────────
parts.append("## Cortex Analysis")
parts.append("")


def _render_cortex(label, result):
    """Render Cortex analyzer results with full taxonomy details.

    Note: Cortex jobs are asynchronous. When the workflow reaches this node,
    jobs may still be in 'Waiting' or 'InProgress' status. The Job ID is
    recorded so results can be queried later from Cortex directly.
    """
    if not result or not isinstance(result, dict):
        parts.append(f"### {label}")
        parts.append("- No data available")
        parts.append("")
        return
    body = result.get("body", result)
    if not isinstance(body, dict):
        parts.append(f"### {label}")
        parts.append(f"- Response: {_safe_str(body)}")
        parts.append("")
        return
    status = body.get("status", "unknown")
    job_id = body.get("id") or body.get("_id", "N/A")

    parts.append(f"### {label}")
    parts.append(f"- **Job ID:** {job_id}")
    parts.append(f"- **Status:** {status}")
    report = body.get("report", {})
    if isinstance(report, dict):
        taxonomies = report.get("summary", {}).get("taxonomies", [])
        if taxonomies:
            parts.append(f"- **Taxonomies ({len(taxonomies)}):**")
            parts.append("")
            parts.append("| Namespace | Predicate | Level | Value |")
            parts.append("|-----------|-----------|-------|-------|")
            for t in taxonomies:
                ns = _safe_str(t.get("namespace", "?"), 30)
                pred = _safe_str(t.get("predicate", "?"), 30)
                level = _safe_str(t.get("level", "?"), 15)
                val = _safe_str(t.get("value", "?"), 30)
                parts.append(f"| {ns} | {pred} | {level} | {val} |")
            parts.append("")
        # Include artifacts if present
        artifacts = report.get("artifacts", [])
        if artifacts:
            parts.append(f"- **Artifacts ({len(artifacts)}):**")
            for a in artifacts[:5]:
                if isinstance(a, dict):
                    parts.append(
                        f"  - `{_safe_str(a.get('data', ''), 60)}` ({a.get('dataType', '?')})"
                    )
            if len(artifacts) > 5:
                parts.append(f"  - ... and {len(artifacts) - 5} more")
            parts.append("")
    else:
        parts.append("- No detailed report available")
        parts.append("")


_render_cortex("Hash Analysis", cortex_hash)
_render_cortex("IP Analysis (primary)", cortex_ip)
_render_cortex("IP Analysis (DShield)", cortex_ip_dshield)
_render_cortex("IP Analysis (Mnemonic pDNS)", cortex_ip_mnemonic_pdns)
_render_cortex("IP Analysis (GoogleDNS)", cortex_ip_googledns)
_render_cortex("IP Analysis (IP-API)", cortex_ip_ipapi)

# ── MISP Threat Intelligence ───────────────────────────────────────────────
parts.append("## Threat Intelligence (MISP)")
parts.append("")
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
        parts.append(f"**IoCs found: {len(attrs)}**")
        parts.append("")
        parts.append("| Type | Value | Category | To IDS |")
        parts.append("|------|-------|----------|--------|")
        for a in attrs[:15]:
            if isinstance(a, dict):
                a_type = _safe_str(a.get("type", "?"), 20)
                a_val = _safe_str(a.get("value", "?"), 60)
                a_cat = _safe_str(a.get("category", "?"), 20)
                a_ids = "Yes" if a.get("to_ids") else "No"
                parts.append(f"| {a_type} | `{a_val}` | {a_cat} | {a_ids} |")
        if len(attrs) > 15:
            parts.append(f"| ... | *{len(attrs) - 15} more IoCs* | ... | ... |")
        parts.append("")
    else:
        parts.append("- No matching IoCs found in MISP")
        parts.append("")
else:
    parts.append("- MISP search not available")
    parts.append("")

# ── Tenzir Network Analysis ────────────────────────────────────────────────
parts.append("## Network Analysis (Tenzir)")
parts.append("")
if tenzir and isinstance(tenzir, dict):
    events = tenzir.get("events", tenzir.get("body", {}).get("events", []))
    if isinstance(events, list) and len(events) > 0:
        parts.append(f"**Network events found: {len(events)}**")
        parts.append("")
        parts.append("| Src IP | Dst IP | Dst Port | Protocol |")
        parts.append("|--------|--------|----------|----------|")
        for evt in events[:10]:
            if isinstance(evt, dict):
                src = _safe_str(evt.get("src_ip", evt.get("source_ip", "?")), 20)
                dst = _safe_str(evt.get("dst_ip", evt.get("destination_ip", "?")), 20)
                port = _safe_str(evt.get("dst_port", evt.get("destination_port", "?")), 10)
                proto = _safe_str(evt.get("protocol", evt.get("proto", "?")), 10)
                parts.append(f"| {src} | {dst} | {port} | {proto} |")
        if len(events) > 10:
            parts.append(f"| ... | ... | ... | *{len(events) - 10} more events* |")
        parts.append("")
    else:
        parts.append("- No network events found")
        parts.append("")
else:
    parts.append("- Tenzir analysis not available")
    parts.append("")

# ── Network Watcher ────────────────────────────────────────────────────────
parts.append("## Active Connections (Network Watcher)")
parts.append("")
if network and isinstance(network, dict):
    connections = network.get("connections", network.get("body", {}).get("connections", []))
    if isinstance(connections, list) and len(connections) > 0:
        parts.append(f"**Active connections: {len(connections)}**")
        parts.append("")
        parts.append("| Remote IP | Remote Port | State | Count |")
        parts.append("|-----------|-------------|-------|-------|")
        for conn in connections[:10]:
            if isinstance(conn, dict):
                ip = _safe_str(conn.get("dst_ip", conn.get("remote_ip", "?")), 20)
                port = _safe_str(conn.get("dst_port", conn.get("remote_port", "?")), 10)
                state = _safe_str(conn.get("state", "?"), 15)
                count = _safe_str(conn.get("count", 1), 10)
                parts.append(f"| {ip} | {port} | {state} | {count} |")
        if len(connections) > 10:
            parts.append(f"| ... | ... | ... | *{len(connections) - 10} more* |")
        parts.append("")
    else:
        parts.append("- No active connections detected")
        parts.append("")
else:
    parts.append("- Network Watcher not available")
    parts.append("")

# ── Loki Log Analysis ──────────────────────────────────────────────────────
parts.append("## Log Analysis (Loki)")
parts.append("")
if loki and isinstance(loki, dict):
    data = loki.get("data", {})
    if isinstance(data, dict):
        results = data.get("result", [])
    else:
        results = []
    if isinstance(results, list) and len(results) > 0:
        total_entries = sum(len(r.get("values", [])) for r in results if isinstance(r, dict))
        parts.append(f"**Log entries found: {total_entries}**")
        parts.append("")
        # Show first few log entries
        shown = 0
        for stream in results:
            if not isinstance(stream, dict) or shown >= 5:
                break
            values = stream.get("values", [])
            labels = stream.get("stream", {})
            label_str = ", ".join(f"{k}={v}" for k, v in labels.items()) if labels else ""
            if label_str:
                parts.append(f"*Stream: {label_str}*")
            for entry in values[:3]:
                if shown >= 5:
                    break
                if isinstance(entry, list) and len(entry) >= 2:
                    ts = _safe_str(entry[0], 25)
                    line = _safe_str(entry[1], 120)
                    parts.append(f"- `{ts}`: {line}")
                elif isinstance(entry, str):
                    parts.append(f"- {_safe_str(entry, 120)}")
                shown += 1
            if shown >= 5:
                break
        if total_entries > 5:
            parts.append(f"- ... and {total_entries - 5} more entries")
        # Show matched ransomware patterns from decision data
        loki_patterns = decision_data.get("loki_patterns", [])
        if loki_patterns:
            parts.append("")
            parts.append(f"**Ransomware patterns matched: {len(loki_patterns)}**")
            parts.append(f"- {', '.join(loki_patterns)}")
        parts.append("")
    else:
        parts.append("- No log entries found")
        parts.append("")
else:
    parts.append("- Loki search not available")
    parts.append("")

# ── Redis Cache ────────────────────────────────────────────────────────────
parts.append("## Optimization (Redis)")
parts.append("")
if redis and isinstance(redis, dict):
    body = redis.get("body", redis)
    if isinstance(body, dict):
        success = body.get("success", False)
        if success:
            parts.append("- IoC cached successfully for future optimizations")
        else:
            parts.append(f"- Cache issue: {_safe_str(body.get('message', body), 80)}")
    else:
        parts.append(f"- Redis response: {_safe_str(body, 80)}")
else:
    parts.append("- Redis cache not available")
parts.append("")

# ── Footer ─────────────────────────────────────────────────────────────────
parts.append("---")
parts.append("*Summary generated by SOAR-Ransomware-Response workflow*")

summary = "\n".join(parts)
print(json.dumps(summary)[1:-1])
