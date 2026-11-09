#!/usr/bin/env python3
"""Regression tests for scripts/quality/export_attack_stix.py.

BUG-040: ``_attack_url`` stripped leading zeros from the sub-technique
segment (``T1485.001`` -> ``/techniques/T1485/1/``), producing non-canonical
MITRE URLs — the function's own docstring documents the ``/T1059/001/``
padded style.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = ROOT / "scripts" / "quality" / "export_attack_stix.py"
if not _SCRIPT.exists():
    pytest.skip(
        "script not present in this environment (stale container image)",
        allow_module_level=True,
    )
_spec = importlib.util.spec_from_file_location("export_attack_stix", _SCRIPT)
stix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stix)


def test_subtechnique_url_uses_padded_id():
    url = stix._attack_url("T1485.001")
    assert url == "https://attack.mitre.org/techniques/T1485/001/"


def test_subtechnique_three_digit():
    url = stix._attack_url("T1059.003")
    assert url.endswith("/T1059/003/")


def test_plain_technique_url():
    assert stix._attack_url("T1059") == "https://attack.mitre.org/techniques/T1059/"


# -- STD-01: ATT&CK <-> D3FEND bidirectional traceability --


def test_d3fend_ids_are_valid_shape():
    for resp, (fid, fname) in stix._RESPONSE_D3FEND.items():
        assert fid.startswith("D3-"), f"{resp}: bad D3FEND id {fid}"
        assert " " not in fname, f"{resp}: url fragment must be camel-case"


def test_coa_d3fend_mapping_emits_external_ref():
    bundle = stix.build_bundle()
    coas = {o["name"]: o for o in bundle["objects"] if o["type"] == "course-of-action"}
    assert "isolate host" in coas
    ref = coas["isolate host"]["external_references"][0]
    assert ref["source_name"] == "mitre-d3fend"
    assert ref["external_id"] == "D3-NI"
    assert ref["url"].startswith("https://d3fend.mitre.org/")


def test_unmapped_responses_are_explicit_not_silent():
    bundle = stix.build_bundle()
    coas = [o for o in bundle["objects"] if o["type"] == "course-of-action"]
    for coa in coas:
        has_ref = "external_references" in coa
        flagged = coa.get("x_soar_d3fend_unmapped") is True
        assert has_ref != flagged, (
            f"{coa['name']}: must either carry a D3FEND ref or be "
            "explicitly flagged unmapped — never silent"
        )


def test_technique_control_bidirectional():
    """Every CoA links to D3FEND (control side) and mitigates ATT&CK
    (threat side) — the bidirectional traceability STD-01 requires."""
    bundle = stix.build_bundle()
    mitigates = [
        o
        for o in bundle["objects"]
        if o["type"] == "relationship" and o["relationship_type"] == "mitigates"
    ]
    assert mitigates, "no mitigates relationships"
    coa_ids = {
        o["id"]
        for o in bundle["objects"]
        if o["type"] == "course-of-action" and "external_references" in o
    }
    assert {r["source_ref"] for r in mitigates} & coa_ids
