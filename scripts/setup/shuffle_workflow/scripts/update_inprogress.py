# Embedded script: update_inprogress
# Confirm case stays active/Open (malicious branch).
# NOTE: TheHive 5's case.status enum only accepts Open/Resolved/Deleted.
# "InProgress" is not a valid case status and PATCHing it always returns
# HTTP 400 AttributeCheckingError. Cases are already created with
# status=Open, so no PATCH is needed here; the case simply remains Open
# (active) while under containment, and mark_false_positive PATCHes it
# to Resolved/FalsePositive on the benign branch instead.
import json
import logging

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
                "reason": f"decision={decision}, no case state change required",
            }
        )
    )
else:
    case_id = r"""$thehive_create_case.body._id"""
    print(
        json.dumps(
            {
                "success": True,
                "status": "Open",
                "case_id": case_id,
                "reason": (
                    "TheHive case.status only supports Open/Resolved/Deleted;"
                    " case remains Open (active) during containment"
                ),
            }
        )
    )
