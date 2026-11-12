# Embedded script: mark_false_positive
# Mark case as FalsePositive (benign branch).
"""Shuffle node: mark the case FalsePositive (benign branch)."""

import json
import logging
import urllib.request

logger = logging.getLogger(__name__)
decision_raw = r"""$calc_decision.message""".strip()
try:
    decision = json.loads(decision_raw).get("decision", "observe")
except Exception:
    decision = "observe"
if decision != "observe":
    print(
        json.dumps(
            {
                "success": True,
                "skipped": True,
                "reason": f"decision={decision}, false-positive resolution not required",
            }
        )
    )
else:
    # Defensive resolution — see containment.py: body={} on upstream
    # failure makes `.body._id` a shuffle_variable_error.
    try:
        _cc = json.loads(r"""$thehive_create_case.message""")
        case_id = ((_cc.get("body") or {}).get("_id") or "")
    except Exception:
        case_id = ""
    if not case_id:
        print(
            json.dumps(
                {
                    "success": True,
                    "skipped": True,
                    "reason": "no case_id — upstream create_case failed",
                }
            )
        )
        raise SystemExit(0)
    url = "__THEHIVE_INT__/api/v1/case/" + case_id
    body = json.dumps({"status": "FalsePositive"}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer __THEHIVE_KEY__"},
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(
                json.dumps({"success": True, "status": resp.status, "body": resp.read().decode()})
            )
    except Exception as e:
        logger.error(json.dumps({"success": False, "exception": str(e)}))
