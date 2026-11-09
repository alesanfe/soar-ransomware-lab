# Embedded script: containment
# Simulated containment action (malicious branch).
"""Shuffle node: simulated containment via Lab API POST /api/v1/contain."""

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)
decision_raw = r"""$calc_decision.message""".strip()
try:
    decision = json.loads(decision_raw).get("decision", "observe")
except Exception:
    decision = "observe"
if decision != "contain":
    print(
        json.dumps(
            {
                "success": True,
                "skipped": True,
                "reason": f"decision={decision}, containment not required",
            }
        )
    )
else:
    hostname = r"""$exec.hostname"""
    alert_id = r"""$exec.alert_id"""
    case_id = r"""$thehive_create_case.message.body._id"""
    body = json.dumps(
        {"hostname": hostname, "alert_id": alert_id, "case_id": case_id, "mode": "simulated"}
    ).encode()
    headers = {"Content-Type": "application/json"}
    service_token = (
        os.environ.get("SOAR_SERVICE_TOKEN")
        or os.environ.get("INTERNAL_SERVICE_TOKEN")
        or "__SERVICE_TOKEN__"
    )
    if service_token.startswith("__"):
        service_token = ""
    if service_token:
        headers["X-Service-Token"] = service_token
    req = urllib.request.Request(
        "http://api:8000/api/v1/contain",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(
                json.dumps({"success": True, "status": resp.status, "body": resp.read().decode()})
            )
    except Exception as e:
        logger.error(json.dumps({"success": False, "exception": str(e)}))
