#!/usr/bin/env python3
"""Unit tests for scripts/maintenance/gen_observe_only_playbook.py.

SOAR-01: the observe-only variant must reuse the detection/enrichment/
decision pipeline while replacing the containment node with a pure
audit action — no HTTP calls, no webhook theft, deterministic output.
"""

from __future__ import annotations

import importlib.util
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "gen_observe_only_playbook",
    ROOT / "scripts" / "maintenance" / "gen_observe_only_playbook.py",
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _playbook(pattern: str) -> Path:
    """Resolve the committed playbook snapshot (filename embeds the live
    workflow id, which Shuffle reassigns on every (re)creation)."""
    matches = sorted((ROOT / "playbooks").glob(pattern))
    assert matches, f"no playbook matching {pattern} under playbooks/"
    return matches[0]


BASE_PLAYBOOK = _playbook("soar-ransomware-response-[0-9a-f]*.json")
LIVE_VARIANT = _playbook("soar-ransomware-response-observeonly-*.json")


def _minimal_base() -> dict:
    """Small workflow exercising every transformation the builder makes."""
    return {
        "id": "aaaaaaaa-0000-0000-0000-000000000000",
        "name": "SOAR-Ransomware-Response",
        "description": "posts to /api/v1/contain when decision=contain",
        "org_id": "org-1",
        "actions": [
            {"id": "act_calc_decision", "label": "calc_decision", "parameters": []},
            {
                "id": "act_containment",
                "label": "containment",
                "parameters": [
                    {"name": "code", "value": "import requests\nrequests.post('/api/v1/contain')"}
                ],
            },
            {"id": "act_update_inprogress", "label": "update_inprogress", "parameters": []},
        ],
        "branches": [
            # Webhook-sourced branch — must be pruned together with the trigger
            # or the start node's parent never completes ("unfinished parents 0/1").
            {
                "id": "br_wh_calc",
                "source_id": "hook-1",
                "destination_id": "act_calc_decision",
            },
            {
                "id": "br_contain",
                "source_id": "act_calc_decision",
                "destination_id": "act_containment",
            },
            {
                "id": "br_after",
                "source_id": "act_containment",
                "destination_id": "act_update_inprogress",
            },
        ],
        "triggers": [
            {"trigger_type": "webhook", "id": "hook-1"},
            {"trigger_type": "schedule", "id": "sched-1"},
        ],
    }


class TestBuildVariant:
    def test_deterministic_output(self):
        base = _minimal_base()
        assert gen.build_variant(base) == gen.build_variant(base)

    def test_name_and_deterministic_id(self):
        variant = gen.build_variant(_minimal_base())
        assert variant["name"] == gen._VARIANT_NAME
        assert variant["id"] == str(uuid.uuid5(uuid.NAMESPACE_DNS, gen._VARIANT_NAME))
        uuid.UUID(variant["id"])  # valid uuid

    def test_server_fields_stripped(self):
        variant = gen.build_variant(_minimal_base())
        assert "org_id" not in variant

    def test_containment_replaced_by_pure_audit(self):
        variant = gen.build_variant(_minimal_base())
        labels = [a.get("label") for a in variant["actions"]]
        assert "containment" not in labels
        observe = next(a for a in variant["actions"] if a.get("label") == "containment_observe")
        assert observe["id"] == "act_containment_observe"
        code = next(p["value"] for p in observe["parameters"] if p["name"] == "code")
        # The observe node must not perform any network call.
        assert "requests" not in code
        assert "http" not in code
        assert "/api/v1/contain" not in code
        assert "observe_only" in code

    def test_branches_repointed(self):
        variant = gen.build_variant(_minimal_base())
        for branch in variant["branches"]:
            assert branch["source_id"] != "act_containment"
            assert branch["destination_id"] != "act_containment"
        edges = {(b["source_id"], b["destination_id"]) for b in variant["branches"]}
        assert ("act_calc_decision", "act_containment_observe") in edges
        assert ("act_containment_observe", "act_update_inprogress") in edges

    def test_webhook_trigger_stripped(self):
        variant = gen.build_variant(_minimal_base())
        kinds = [t.get("trigger_type") for t in variant["triggers"]]
        assert "webhook" not in kinds
        assert "schedule" in kinds  # non-webhook triggers preserved

    def test_webhook_sourced_branches_pruned(self):
        """Branches fed by a removed trigger must not leave phantom parents."""
        variant = gen.build_variant(_minimal_base())
        sources = {b.get("source_id") for b in variant["branches"]}
        assert "hook-1" not in sources
        assert all(b["id"] != "br_wh_calc" for b in variant["branches"])

    def test_base_not_mutated(self):
        base = _minimal_base()
        snapshot = json.loads(json.dumps(base))
        gen.build_variant(base)
        assert base == snapshot

    def test_action_count_preserved(self):
        variant = gen.build_variant(_minimal_base())
        assert len(variant["actions"]) == 3


class TestRealPlaybookArtifacts:
    """Guard the committed GitOps artifacts against drift."""

    def test_base_export_contains_real_containment(self):
        base = json.loads(BASE_PLAYBOOK.read_text(encoding="utf-8"))
        containment = [a for a in base["actions"] if a.get("label") == "containment"]
        assert len(containment) == 1
        code = json.dumps(containment[0])
        assert "/api/v1/contain" in code  # supervised playbook still protects

    def test_variant_generation_from_real_base(self):
        base = json.loads(BASE_PLAYBOOK.read_text(encoding="utf-8"))
        variant = gen.build_variant(base)
        assert len(variant["actions"]) == len(base["actions"])
        assert all(t.get("trigger_type") != "webhook" for t in variant["triggers"])

    def test_live_artifact_is_observe_only(self):
        """The committed live export must carry the observe node and no
        executable containment code."""
        live = json.loads(LIVE_VARIANT.read_text(encoding="utf-8"))
        labels = [a.get("label") for a in live["actions"]]
        assert "containment" not in labels
        # No dangling branches from removed webhook triggers — the worker
        # would wait forever on the start node's phantom parent.
        trigger_ids = {t.get("id") for t in live.get("triggers", [])}
        action_ids = {a.get("id") for a in live["actions"]}
        for branch in live.get("branches", []):
            assert branch.get("source_id") in action_ids | trigger_ids
        observe = next(a for a in live["actions"] if a.get("label") == "containment_observe")
        code = next(p["value"] for p in observe["parameters"] if p["name"] == "code")
        assert "requests" not in code
        assert "/api/v1/contain" not in code
        # Any remaining textual reference is prose only (description),
        # never executable action code.
        for action in live["actions"]:
            for param in action.get("parameters", []):
                if param.get("name") == "code":
                    assert "/api/v1/contain" not in str(param.get("value"))
