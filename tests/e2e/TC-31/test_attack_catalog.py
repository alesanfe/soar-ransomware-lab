"""TC-31 — versioned ATT&CK catalog validation.

Every sigma rule's MITRE tags are checked against detections/attack-catalog.yaml:
technique exists in the versioned catalog, is not deprecated, and maps at least
one D3FEND countermeasure. Catalog itself must be versioned and well-formed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

DETECTIONS = Path("/app/detections")
SIGMA_DIR = DETECTIONS / "sigma"
CATALOG = DETECTIONS / "attack-catalog.yaml"

TECH_RE = re.compile(r"^attack\.t\d{4}(\.\d{3})?$")
TECH_ID_RE = re.compile(r"^t\d{4}(\.\d{3})?$")


def _load_catalog() -> dict:
    assert CATALOG.exists(), "attack-catalog.yaml missing"
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _rule_techniques() -> dict[str, list[str]]:
    """{rule_file: [tXXXX technique ids declared as tags]}."""
    out: dict[str, list[str]] = {}
    for f in sorted(SIGMA_DIR.glob("*.yml")):
        rule = yaml.safe_load(f.read_text(encoding="utf-8"))
        tags = rule.get("tags") or []
        out[f.name] = [t.split(".", 1)[1] for t in tags if TECH_RE.match(t)]
    return out


@pytest.mark.e2e
class TestAttackCatalog:
    def test_catalog_versioned_and_wellformed(self):
        cat = _load_catalog()
        assert re.match(r"^\d{4}-\d{2}$", str(cat.get("version", ""))), "catalog version missing/malformed"
        for tid, entry in (cat.get("techniques") or {}).items():
            assert TECH_ID_RE.match(tid), f"bad technique id: {tid}"
            assert entry.get("name"), f"{tid} missing name"
            assert entry.get("d3fend"), f"{tid} maps no D3FEND countermeasure"
        for tid in cat.get("deprecated") or {}:
            assert TECH_ID_RE.match(tid), f"bad deprecated id: {tid}"

    def test_no_rule_uses_deprecated_technique(self):
        cat = _load_catalog()
        deprecated = set((cat.get("deprecated") or {}).keys())
        # also flag parents of deprecated sub-techniques and vice versa
        for fname, techs in _rule_techniques().items():
            for t in techs:
                assert t not in deprecated, f"{fname}: uses deprecated technique {t}"
                parent = t.split(".")[0]
                assert parent not in deprecated or t in cat["techniques"], (
                    f"{fname}: {t} hangs off deprecated parent {parent}"
                )

    def test_every_tagged_technique_in_versioned_catalog(self):
        cat = _load_catalog()
        known = set((cat.get("techniques") or {}).keys())
        for fname, techs in _rule_techniques().items():
            missing = [t for t in techs if t not in known]
            assert not missing, f"{fname}: techniques not in catalog v{cat['version']}: {missing}"

    def test_every_used_technique_has_d3fend_coverage(self):
        cat = _load_catalog()
        techs = cat.get("techniques") or {}
        for fname, used in _rule_techniques().items():
            for t in used:
                if t in techs:
                    assert techs[t].get("d3fend"), f"{fname}: {t} has no D3FEND countermeasure"

    def test_technique_tag_format_is_stix_attack_pattern(self):
        # every MITRE tag must parse as a STIX attack-pattern external id
        for fname, tags in (
            (f.name, (yaml.safe_load(f.read_text(encoding="utf-8")).get("tags") or []))
            for f in sorted(SIGMA_DIR.glob("*.yml"))
        ):
            for tag in tags:
                if tag.startswith("attack.t"):
                    assert TECH_RE.match(tag), f"{fname}: malformed technique tag {tag}"
