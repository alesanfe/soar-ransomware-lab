# Embedded script: notify_critical
# Notify critical (malicious branch).
import json
import logging
import time

logger = logging.getLogger(__name__)
alert_id = r"""$exec.alert_id"""
hostname = r"""$exec.hostname"""
case_id = r"""$thehive_create_case.body._id"""
decision_raw = r"""$calc_decision.message"""
try:
    d = json.loads(decision_raw)
    decision = d.get("decision", "observe")
    score = d.get("score", 0)
    verdict = d.get("verdict", "unknown")
except Exception:
    decision = "observe"
    score = 0
    verdict = "unknown"
if decision != "contain":
    print(
        json.dumps(
            {
                "success": True,
                "skipped": True,
                "reason": f"decision={decision}, critical notification not required",
            }
        )
    )
else:
    notification = {
        "success": True,
        "skipped": False,
        "channel": "email",
        "severity": "CRITICAL",
        "subject": f"[CRITICAL] Ransomware detected - {hostname} contained",
        "body": (
            f"Alert: {alert_id} | Host: {hostname} | Case: {case_id}"
            f" | Score: {score} | Verdict: {verdict}"
        ),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(json.dumps(notification))
