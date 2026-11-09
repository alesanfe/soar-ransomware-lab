#!/usr/bin/env python3
"""Export the lab's MITRE ATT&CK coverage as a STIX 2.1 bundle (VAL-008).

Scans the canonical sources of technique coverage —
``tests/e2e/fixtures/malware_scenarios.json`` (scenario -> techniques ->
expected response), ``gminst4ll_iocs.json``, ``simulate_alerts.py`` and
the workflow decision script — and emits a STIX 2.1 bundle containing:

- ``attack-pattern`` SDOs for every T1xxx / T1xxx.xxx identifier, with
  an ``external_references`` entry pointing to attack.mitre.org.
  Sub-techniques are distinguished via the ``x_mitre_is_subtechnique``
  flag and a dotted external id.
- ``course-of-action`` SDOs for each response action the playbook can
  execute (isolate_host, block_ip, contain_exfiltration, ...).
- ``grouping`` SDOs per test scenario linking the techniques it
  exercises with the responses the playbook is expected to take.
- ``relationship`` SDOs ``course-of-action --mitigates--> attack-pattern``
  derived from scenario expected_response links, making the
  detection->response traceability machine-readable.

IDs are deterministic (uuid5) so the bundle is diff-able across runs.

Usage::

    python scripts/quality/export_attack_stix.py
    python scripts/quality/export_attack_stix.py --validate-only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "reports" / "stix"
STIX_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://soar-lab/stix/attack-coverage")
TID_RE = re.compile(r"T1\d{3}(?:\.\d{3})?")

SCAN_FILES = [
    ROOT / "tests" / "e2e" / "fixtures" / "malware_scenarios.json",
    ROOT / "tests" / "e2e" / "fixtures" / "gminst4ll_iocs.json",
    ROOT / "tests" / "e2e" / "fixtures" / "expected_workflows.json",
    ROOT / "src" / "soar_lab" / "simulator" / "simulate_alerts.py",
    ROOT / "scripts" / "setup" / "shuffle_workflow" / "scripts" / "calc_decision.py",
    ROOT / "tests" / "conftest.py",
    ROOT / "docs" / "04-operations.md",
]
SCAN_DIRS = [ROOT / "tests" / "e2e", ROOT / "tests" / "atomic"]

NOW = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sid(stix_type: str, key: str) -> str:
    return f"{stix_type}--{uuid.uuid5(STIX_NS, f'{stix_type}:{key}')}"


def _attack_url(tid: str) -> str:
    """ATT&CK URL: sub-techniques use /techniques/T1059/001/ style."""
    if "." in tid:
        base, sub = tid.split(".")
        return f"https://attack.mitre.org/techniques/{base}/{sub}/"
    return f"https://attack.mitre.org/techniques/{tid}/"


# ATT&CK -> D3FEND reverse traceability for each response action.
# IDs verified against https://d3fend.mitre.org/ontologies/d3fend.csv.
_D3FEND_URL = "https://d3fend.mitre.org/technique/d3f:{name}/"
_RESPONSE_D3FEND: dict[str, tuple[str, str]] = {
    "block_c2_channel": ("D3-OTF", "OutboundTrafficFiltering"),
    "block_ip": ("D3-NTF", "NetworkTrafficFiltering"),
    "block_mining_domain": ("D3-DNSDL", "DNSDenylisting"),
    "block_mining_pool": ("D3-OTF", "OutboundTrafficFiltering"),
    "block_smb": ("D3-BDI", "BroadcastDomainIsolation"),
    "contain_exfiltration": ("D3-OTF", "OutboundTrafficFiltering"),
    "contain_lateral_movement": ("D3-BDI", "BroadcastDomainIsolation"),
    "isolate_affected_hosts": ("D3-NI", "NetworkIsolation"),
    "isolate_host": ("D3-NI", "NetworkIsolation"),
    "patch_vulnerability": ("D3-SU", "SoftwareUpdate"),
    "terminate_browser_process": ("D3-PT", "ProcessTermination"),
    "terminate_process": ("D3-PT", "ProcessTermination"),
    # preserve_evidence has no D3FEND countermeasure (forensic
    # preservation is outside the ontology's defensive-action scope) —
    # emitted explicitly unmapped rather than force-fitted.
}


def _d3fend_ref(resp: str) -> list[dict[str, str]]:
    """D3FEND external_reference for a response action, or empty."""
    if resp not in _RESPONSE_D3FEND:
        return []
    fid, fname = _RESPONSE_D3FEND[resp]
    return [
        {
            "source_name": "mitre-d3fend",
            "external_id": fid,
            "url": _D3FEND_URL.format(name=fname),
        }
    ]


def _collect_techniques() -> set[str]:
    tids: set[str] = set()
    for path in SCAN_FILES:
        if path.exists():
            tids.update(TID_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    for scan_dir in SCAN_DIRS:
        for path in sorted(scan_dir.rglob("*.py")) + sorted(scan_dir.rglob("*.json")):
            tids.update(TID_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return tids


def _load_scenarios() -> list[dict[str, Any]]:
    path = ROOT / "tests" / "e2e" / "fixtures" / "malware_scenarios.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [s for group in data.values() for s in group]


def build_bundle() -> dict[str, Any]:
    tids = sorted(_collect_techniques())
    scenarios = _load_scenarios()
    objects: list[dict[str, Any]] = []
    responses: set[str] = set()

    for tid in tids:
        is_sub = "." in tid
        obj: dict[str, Any] = {
            "type": "attack-pattern",
            "spec_version": "2.1",
            "id": _sid("attack-pattern", tid),
            "created": NOW,
            "modified": NOW,
            "name": f"MITRE ATT&CK {tid}",
            "description": (
                f"Technique {'sub-technique ' if is_sub else ''}exercised by the "
                "SOAR ransomware lab test scenarios."
            ),
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": tid,
                    "url": _attack_url(tid),
                }
            ],
        }
        if is_sub:
            obj["x_mitre_is_subtechnique"] = True
        objects.append(obj)

    for sc in scenarios:
        responses.update(sc.get("expected_response", []))

    for resp in sorted(responses):
        coa: dict[str, Any] = {
            "type": "course-of-action",
            "spec_version": "2.1",
            "id": _sid("course-of-action", resp),
            "created": NOW,
            "modified": NOW,
            "name": resp.replace("_", " "),
            "description": (
                f"Automated response action '{resp}' implemented by the "
                "SOAR playbook (Shuffle workflow containment node)."
            ),
        }
        refs = _d3fend_ref(resp)
        if refs:
            coa["external_references"] = refs
        else:
            coa["x_soar_d3fend_unmapped"] = True
        objects.append(coa)

    # scenario groupings + mitigates relationships (dedup: several
    # scenarios share the same response/technique pair)
    emitted_rel: set[str] = set()
    for sc in scenarios:
        refs: list[str] = []
        for tid in sc.get("mitre_techniques", []):
            ap = _sid("attack-pattern", tid)
            refs.append(ap)
            for resp in sc.get("expected_response", []):
                rel_id = _sid("relationship", f"{resp}:mitigates:{tid}")
                if rel_id in emitted_rel:
                    continue
                emitted_rel.add(rel_id)
                objects.append(
                    {
                        "type": "relationship",
                        "spec_version": "2.1",
                        "id": rel_id,
                        "created": NOW,
                        "modified": NOW,
                        "relationship_type": "mitigates",
                        "source_ref": _sid("course-of-action", resp),
                        "target_ref": ap,
                        "description": f"'{resp}' mitigates {tid} in scenario '{sc['name']}'",
                    }
                )
        for resp in sc.get("expected_response", []):
            refs.append(_sid("course-of-action", resp))
        if refs:
            objects.append(
                {
                    "type": "grouping",
                    "spec_version": "2.1",
                    "id": _sid("grouping", sc["name"]),
                    "created": NOW,
                    "modified": NOW,
                    "name": f"scenario: {sc['name']}",
                    "context": "suspicious-activity",
                    "description": sc.get("description", ""),
                    "object_refs": sorted(set(refs)),
                }
            )

    identity = {
        "type": "identity",
        "spec_version": "2.1",
        "id": _sid("identity", "soar-lab"),
        "created": NOW,
        "modified": NOW,
        "name": "SOAR Ransomware Lab",
        "identity_class": "system",
        "description": "Academic SOAR laboratory — ATT&CK coverage export",
    }
    objects.insert(0, identity)

    return {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid5(STIX_NS, 'attack-coverage-bundle')}",
        "objects": objects,
    }


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    """Structural STIX 2.1 check: ids, required fields, resolvable refs."""
    errors: list[str] = []
    if bundle.get("type") != "bundle":
        errors.append("root object is not a STIX bundle")
    objects = bundle.get("objects", [])
    ids = {o.get("id") for o in objects}
    if len(ids) != len(objects):
        errors.append("duplicate object ids in bundle")
    stix_id = re.compile(r"^[a-z0-9-]+--[0-9a-f-]{36}$")
    for obj in objects:
        oid = obj.get("id", "")
        if not stix_id.match(oid):
            errors.append(f"malformed STIX id '{oid}'")
        for field in ("type", "created", "modified"):
            if field not in obj:
                errors.append(f"{oid}: missing '{field}'")
        if obj.get("type") == "attack-pattern":
            refs = obj.get("external_references", [])
            if not any(r.get("source_name") == "mitre-attack" for r in refs):
                errors.append(f"{oid}: attack-pattern lacks mitre-attack reference")
        if obj.get("type") == "relationship":
            for field in ("relationship_type", "source_ref", "target_ref"):
                if field not in obj:
                    errors.append(f"{oid}: relationship missing '{field}'")
            for ref in (obj.get("source_ref"), obj.get("target_ref")):
                if ref not in ids:
                    errors.append(f"{oid}: dangling ref '{ref}'")
        if obj.get("type") == "grouping":
            for ref in obj.get("object_refs", []):
                if ref not in ids:
                    errors.append(f"{oid}: dangling object_ref '{ref}'")
    if not any(o.get("type") == "attack-pattern" for o in objects):
        errors.append("bundle contains no attack-pattern objects")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=OUT_DIR / "attack_coverage.stix.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        bundle = json.loads(args.output.read_text(encoding="utf-8"))
    else:
        bundle = build_bundle()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        n_tech = sum(1 for o in bundle["objects"] if o["type"] == "attack-pattern")
        print(
            f"STIX bundle written: {args.output} "
            f"({len(bundle['objects'])} objects, {n_tech} techniques)"
        )

    errors = validate_bundle(bundle)
    if errors:
        for e in errors:
            print(f"INVALID: {e}")
        return 1
    print("STIX structural validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
