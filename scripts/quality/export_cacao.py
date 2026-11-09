#!/usr/bin/env python3
"""Export the SOAR Shuffle workflow to a CACAO 2.0 playbook.

The lab's SOAR playbook lives in Shuffle's proprietary JSON format
(``scripts/setup/shuffle_workflow/``). CACAO (Collaborative Automated
Course of Action Operations, OASIS) is the open standard for sharing
security playbooks — this converter makes the lab's response procedure
interoperable.

Mapping
-------
- Webhook trigger            -> ``start`` step (trigger documented in the
  playbook description; CACAO triggers live in ``trigger_definitions``)
- ``action`` node (http app) -> ``action`` step with an ``http-api``
  command (method + URL; headers/body in the command description)
- ``execute_python`` node    -> ``action`` step with a ``custom`` command
  carrying the embedded code base64-encoded in ``command_b64``
- Fan-out (1 node -> N edges)-> intermediate ``parallel`` step with the
  children in ``next_steps``
- ``act_calc_decision``      -> ``action`` step whose single outgoing
  ``parallel`` is replaced by an ``if-condition`` step:
  ``alert.decision == 'contain'`` -> containment path / else -> observe
  path. Shuffle 2.2.1 cannot express this natively (its branch
  conditions never evaluate), so the export is *more* faithful than the
  runtime graph — documented, not hidden.
- Leaf actions               -> ``on_completion`` -> shared ``end`` step

Step IDs are deterministic (uuid5 over the Shuffle node id) so exports
are reproducible and diff-able.

Usage::

    python scripts/quality/export_cacao.py                 # writes reports/cacao/playbook.json
    python scripts/quality/export_cacao.py --validate-only # structural check of last export
    python scripts/quality/export_cacao.py --input wf.json # convert an exported Shuffle JSON
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "setup"))

CACAO_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://soar-lab/cacao/playbook")
OUT_DIR = ROOT / "reports" / "cacao"
DECISION_NODE = "act_calc_decision"
CONTAINMENT_NODE = "act_containment"


def _sid(step_type: str, node_id: str) -> str:
    """Deterministic CACAO step id: ``<type>--<uuid5>``."""
    return f"{step_type}--{uuid.uuid5(CACAO_NS, node_id)}"


def _params_dict(action: dict[str, Any]) -> dict[str, str]:
    return {
        p.get("name", ""): str(p.get("value", ""))
        for p in action.get("parameters", [])
        if isinstance(p, dict)
    }


def _command_for(action: dict[str, Any]) -> dict[str, Any]:
    """Map a Shuffle action to a CACAO command object."""
    params = _params_dict(action)
    if action.get("app_name") == "Shuffle Tools" and "code" in params:
        return {
            "type": "custom",
            "command": f"execute_python:{action.get('label', action.get('id'))}",
            "command_b64": base64.b64encode(params["code"].encode()).decode(),
            "description": "Embedded Python executed by Shuffle Tools",
        }
    method = action.get("action_name") or action.get("name") or "HTTP"
    parts = [f"{method} {params.get('url', '').strip()}".strip()]
    if params.get("headers"):
        parts.append(f"headers: {params['headers']}")
    if params.get("body"):
        parts.append(f"body: {params['body']}")
    return {
        "type": "http-api",
        "command": parts[0],
        "description": "\n".join(parts[1:]) or "HTTP call via Shuffle http app",
    }


def _agent_for(action: dict[str, Any]) -> str | None:
    """Infer the target system from the action's URL/app."""
    url = _params_dict(action).get("url", "")
    for key, agent in (
        ("thehive", "thehive"),
        ("cortex", "cortex"),
        ("misp", "misp"),
        ("elasticsearch", "elasticsearch"),
        ("loki", "loki"),
        ("redis", "redis"),
        ("tenzir", "tenzir"),
        ("api/v1", "soar-api"),
    ):
        if key in url:
            return agent
    return "shuffle" if action.get("app_name") == "Shuffle Tools" else None


def convert(definition: dict[str, Any]) -> dict[str, Any]:
    """Convert a Shuffle workflow definition dict to a CACAO 2.0 playbook."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    actions = {a["id"]: a for a in definition.get("actions", [])}
    branches = definition.get("branches", [])

    # outgoing edges per node
    outgoing: dict[str, list[str]] = {}
    for b in branches:
        outgoing.setdefault(b["source_id"], []).append(b["destination_id"])

    workflow: dict[str, Any] = {}
    agents: dict[str, Any] = {}

    # start step driven by the webhook trigger
    start_id = _sid("start", "start")
    first = definition.get("start") or (definition["actions"][0]["id"])
    workflow[start_id] = {
        "type": "start",
        "name": "webhook-intake",
        "description": (
            "Entry point: Shuffle webhook trigger receives the SIEM "
            "ransomware alert (see trigger '"
            + (definition.get("triggers") or [{}])[0].get("name", "Webhook")
            + "' in the source workflow)."
        ),
        "on_completion": _sid("action", first),
    }

    used_parallel = 0
    for node_id, node in actions.items():
        step_id = _sid("action", node_id)
        dests = outgoing.get(node_id, [])
        agent = _agent_for(node)
        step: dict[str, Any] = {
            "type": "action",
            "name": node.get("label") or node_id,
            "description": (
                f"Shuffle action '{node_id}' "
                f"({node.get('app_name', '?')} {node.get('app_version', '')})"
            ),
            "commands": [_command_for(node)],
        }
        if agent:
            agents[agent] = {
                "type": "security-category",
                "name": agent,
                "description": f"SOAR lab service '{agent}' reached via Shuffle http/python nodes",
            }
            step["agent"] = f"agent--{agent}"

        if len(dests) == 1:
            step["on_completion"] = _sid("action", dests[0])
        elif len(dests) > 1:
            # fan-out -> parallel step; the decision node gets a real
            # if-condition instead (see note in module docstring)
            if node_id == DECISION_NODE:
                cond_id = _sid("if-condition", node_id + ":decision")
                contain = [d for d in dests if d == CONTAINMENT_NODE]
                observe = [d for d in dests if d != CONTAINMENT_NODE]
                step["on_completion"] = cond_id
                workflow[cond_id] = {
                    "type": "if-condition",
                    "name": "verdict == contain",
                    "condition": "$calc_decision.message.decision == 'contain'",
                    "description": (
                        "Decision gate: malicious verdict -> containment "
                        "path; benign -> false-positive/observe path. In "
                        "Shuffle this is emulated by unconditional edges "
                        "plus internal guards inside each downstream node."
                    ),
                    "on_true": _sid("action", contain[0]) if contain else _sid("end", "end"),
                    "on_false": _sid("action", observe[0]) if observe else _sid("end", "end"),
                }
            else:
                used_parallel += 1
                par_id = _sid("parallel", f"{node_id}:fanout")
                step["on_completion"] = par_id
                workflow[par_id] = {
                    "type": "parallel",
                    "name": f"fan-out after {node.get('label') or node_id}",
                    "description": f"Parallel fan-out of Shuffle node '{node_id}'",
                    "next_steps": [_sid("action", d) for d in dests],
                }
        else:
            step["on_completion"] = _sid("end", "end")
        workflow[step_id] = step

    end_id = _sid("end", "end")
    workflow[end_id] = {
        "type": "end",
        "name": "response-complete",
        "description": "Terminal step: metrics indexed and case enriched.",
    }

    return {
        "type": "playbook",
        "spec_version": "cacao-2.0",
        "id": f"playbook--{uuid.uuid5(CACAO_NS, definition.get('name', 'wf'))}",
        "name": definition.get("name", "SOAR playbook"),
        "description": definition.get("description", ""),
        "playbook_types": ["enrichment", "remediation", "notification"],
        "created_by": f"identity--{uuid.uuid5(CACAO_NS, 'soar-lab')}",
        "created": now,
        "modified": now,
        "workflow_start": start_id,
        "workflow": workflow,
        "agent_definitions": agents,
        "unmet_requirements": {
            "note": (
                "Elements without direct CACAO equivalence: per-node "
                "canvas positions, Shuffle $variable bindings "
                "($exec.*, $node.body), retry/auth policies embedded in "
                "parameters, and runtime-added Cortex analyzer nodes "
                "(dynamic actions appended at deploy time)."
            )
        },
    }


def validate_playbook(pb: dict[str, Any]) -> list[str]:
    """Structural check: ids unique, edges resolvable, graph reachable."""
    errors: list[str] = []
    if pb.get("spec_version") != "cacao-2.0" or pb.get("type") != "playbook":
        errors.append("missing CACAO envelope (type=playbook, spec_version=cacao-2.0)")
    wf = pb.get("workflow", {})
    start = pb.get("workflow_start")
    if start not in wf:
        errors.append(f"workflow_start '{start}' not in workflow")
        return errors
    for sid, step in wf.items():
        if "type" not in step:
            errors.append(f"step {sid} missing 'type'")
        for key in ("on_completion", "on_true", "on_false", "on_success", "on_failure"):
            if step.get(key) and step[key] not in wf:
                errors.append(f"step {sid}.{key} -> unknown '{step[key]}'")
        for nxt in step.get("next_steps", []):
            if nxt not in wf:
                errors.append(f"parallel {sid} -> unknown '{nxt}'")
    # reachability from start
    seen, stack = set(), [start]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        step = wf.get(cur, {})
        stack += [
            t
            for t in (
                step.get("on_completion"),
                step.get("on_true"),
                step.get("on_false"),
                step.get("on_success"),
                step.get("on_failure"),
                *(step.get("next_steps") or []),
            )
            if t
        ]
    for orphan in set(wf) - seen:
        errors.append(f"unreachable step '{orphan}'")
    return errors


def _load_definition(path: Path | None) -> dict[str, Any]:
    if path:
        return json.loads(path.read_text(encoding="utf-8"))
    # Build the base definition with a dummy context (static graph —
    # dynamic analyzer nodes are runtime additions, documented in
    # unmet_requirements).
    from shuffle_workflow.workflow_actions import WorkflowContext
    from shuffle_workflow.workflow_definition import build_workflow_definition

    ctx = WorkflowContext(
        thehive_key="key",
        cortex_key="key",
        misp_key="key",
        app_id_http="app",
        app_id_shuffle_tools="tools",
        cortex_basic="YQ==",
        es_basic="YQ==",
    )
    return build_workflow_definition(ctx)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Shuffle workflow JSON to convert")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUT_DIR / "soar_ransomware_response.cacao.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        pb = json.loads(args.output.read_text(encoding="utf-8"))
    else:
        definition = _load_definition(args.input)
        pb = convert(definition)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(pb, indent=2), encoding="utf-8")
        n_steps = len(pb["workflow"])
        print(f"CACAO playbook written: {args.output} ({n_steps} steps)")

    errors = validate_playbook(pb)
    if errors:
        for e in errors:
            print(f"INVALID: {e}")
        return 1
    print("CACAO structural validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
