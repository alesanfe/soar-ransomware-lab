"""Generate the observe-only playbook variant (SOAR-01, 2nd playbook).

Reads the exported ``SOAR-Ransomware-Response`` playbook from
``playbooks/`` (GitOps source of truth, IR2) and emits a variant where
the ``containment`` node is replaced by an audit-only action: the
pipeline detects and decides exactly the same, but instead of calling
``/api/v1/contain`` it records the decision payload as the node result.

Use case: safe-by-default deployments — the full enrichment chain runs
and decisions stay explainable, but no containment is ever attempted
until an operator promotes the supervised playbook.

Canonical flow (draft → deploy → snapshot):

1. Generate the draft (deterministic uuid5 id, webhook stripped so the
   variant cannot steal the SIEM hook and double-fire):

       python scripts/maintenance/gen_observe_only_playbook.py \
           --base playbooks/soar-ransomware-response-<id8>.json \
           --out /tmp/observe_only_draft.json

2. Import into Shuffle (``POST /api/v1/workflows`` via ShuffleClient —
   the backend assigns the final workflow id server-side).

3. Re-export so ``playbooks/`` mirrors what Shuffle actually runs:

       python scripts/maintenance/export_workflows.py --out playbooks

   The committed artifact is the server-exported file
   ``soar-ransomware-response-observeonly-<live-id8>.json`` — same
   convention as the base playbook export.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

OBSERVE_ONLY_CODE = '''# Embedded script: containment (observe-only variant)
# SOAR-01 supervised variant — records the decision instead of acting.
import json
import logging

logger = logging.getLogger(__name__)
decision_raw = r"""$calc_decision.message""".strip()
try:
    decision_doc = json.loads(decision_raw)
except Exception:
    decision_doc = {"decision": "unparsable", "raw": decision_raw[:500]}

print(
    json.dumps(
        {
            "success": True,
            "mode": "observe_only",
            "action_taken": False,
            "recorded_decision": decision_doc,
        }
    )
)
'''

_VARIANT_NAME = "SOAR-Ransomware-Response-ObserveOnly"
_VARIANT_DESCRIPTION = (
    "Observe-only variant of SOAR-Ransomware-Response: identical "
    "detect→enrich→decide pipeline; the containment node records the "
    "verdict instead of calling /api/v1/contain. Promote to the full "
    "playbook to enable containment."
)


def build_variant(base: dict) -> dict:
    """Return the observe-only playbook derived from the base export."""
    wf = json.loads(json.dumps(base))  # deep copy via JSON round-trip
    wf["name"] = _VARIANT_NAME
    wf["description"] = _VARIANT_DESCRIPTION
    # Deterministic id derived from the variant name — re-generation is
    # idempotent (GitOps diffs stay empty).
    wf["id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, _VARIANT_NAME))
    for server_field in ("org_id", "execution_org", "published_id", "revision_id"):
        wf.pop(server_field, None)
    # The variant must not steal the SIEM webhook — two workflows bound to
    # one hook double-fire. It runs manually or as a subflow.
    removed_ids = {
        t.get("id") for t in wf.get("triggers", []) if t.get("trigger_type") == "webhook"
    }
    wf["triggers"] = [t for t in wf.get("triggers", []) if t.get("trigger_type") != "webhook"]
    # Branches sourced at a removed trigger would leave their targets with a
    # phantom parent — the worker waits forever on it ("unfinished parents
    # 0/1"). Prune them so the start node stays parentless.
    wf["branches"] = [b for b in wf.get("branches", []) if b.get("source_id") not in removed_ids]
    for action in wf.get("actions", []):
        if action.get("label") != "containment":
            continue
        for param in action.get("parameters", []):
            if param.get("name") == "code":
                param["value"] = OBSERVE_ONLY_CODE
        action["label"] = "containment_observe"
        action["id"] = "act_containment_observe"
    # Repoint branches that targeted the containment node.
    for branch in wf.get("branches", []):
        if branch.get("destination_id") == "act_containment":
            branch["destination_id"] = "act_containment_observe"
        if branch.get("source_id") == "act_containment":
            branch["source_id"] = "act_containment_observe"
        if isinstance(branch.get("id"), str) and "contain" in branch["id"]:
            branch["id"] = branch["id"].replace("contain", "contain_observe")
    return wf


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Path to the exported base playbook JSON")
    ap.add_argument("--out", required=True, help="Output path for the variant playbook JSON")
    args = ap.parse_args()

    base = json.loads(Path(args.base).read_text(encoding="utf-8"))
    variant = build_variant(base)
    out = Path(args.out)
    out.write_text(json.dumps(variant, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out} (id={variant['id']}, {len(variant.get('actions', []))} actions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
