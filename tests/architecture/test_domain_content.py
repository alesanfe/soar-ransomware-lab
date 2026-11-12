#!/usr/bin/env python3
"""Static validators for domain content (DOM-EVAL-*): sigma rules, the
ATT&CK/D3FEND catalog, and the embedded Shuffle playbook scripts.

These mirror TC-24/TC-31 but run offline — no stack needed — and add
checks the e2e tests don't cover:

- condition expressions must only reference declared selections
- every technique a rule MATCHES must be tagged (DOM-EVAL-001: the
  impact rule matched T1490/T1491 but only tagged T1486)
- every ``__PLACEHOLDER__`` in an embedded script must have a
  ``.replace("__X__", ...)`` applied at its ``load()`` site in
  workflow_actions.py — an unsubstituted placeholder ships a literal
  token to Shuffle and the node fails at runtime
- containment must self-guard on the decision (Shuffle 2.2.1 branches
  never evaluate — the node itself is the guard)
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SIGMA_DIR = ROOT / "detections/sigma"
CATALOG = ROOT / "detections/attack-catalog.yaml"
WF_ACTIONS = ROOT / "scripts/setup/shuffle_workflow/workflow_actions.py"
SCRIPTS_DIR = ROOT / "scripts/setup/shuffle_workflow/scripts"
EXPORT_CACAO = ROOT / "scripts/quality/export_cacao.py"
EXPORT_STIX = ROOT / "scripts/quality/export_attack_stix.py"

TECH_TAG_RE = re.compile(r"^attack\.t\d{4}(\.\d{3})?$")
TECH_ID_RE = re.compile(r"^T\d{4}(\.\d{3})?$", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]+__")


def _rules() -> dict[str, dict]:
    return {
        f.name: yaml.safe_load(f.read_text(encoding="utf-8"))
        for f in sorted(SIGMA_DIR.glob("*.yml"))
    }


@pytest.fixture(scope="module")
def catalog() -> dict:
    return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rules() -> dict:
    return _rules()


# ---------------------------------------------------------------------------
# Sigma well-formedness (static mirror of TC-24/TC-31)
# ---------------------------------------------------------------------------


def test_rules_are_wellformed_sigma(rules):
    assert len(rules) >= 6, "rule inventory shrank"
    for name, rule in rules.items():
        for field in ("title", "id", "status", "logsource", "detection", "level", "tags"):
            assert rule.get(field), f"{name}: missing {field}"
        assert rule["detection"].get("condition"), f"{name}: no condition"


def test_conditions_reference_declared_selections(rules):
    """`1 of selection_*` needs ≥1 selection_* key; `selection` needs the
    selection key. A typo silently yields a never-firing rule."""
    for name, rule in rules.items():
        det = rule["detection"]
        selections = {k for k in det if k != "condition"}
        cond = det["condition"]
        for ref in re.findall(r"selection[\w]*\*?", cond):
            if ref.endswith("*"):
                prefix = ref[:-1]
                assert any(s.startswith(prefix) for s in selections), (
                    f"{name}: condition {cond!r} matches no declared selection"
                )
            else:
                assert ref in selections, (
                    f"{name}: condition references undeclared {ref!r}"
                )


def test_matched_techniques_are_tagged(rules):
    """DOM-EVAL-001: technique ids used INSIDE detection selections must
    also appear as attack.t* tags — coverage attribution counts tags."""
    for name, rule in rules.items():
        tagged = {
            t.split(".", 1)[1].lower()
            for t in rule.get("tags") or []
            if TECH_TAG_RE.match(t)
        }
        det_text = yaml.safe_dump(rule["detection"])
        matched = {t.lower() for t in TECH_ID_RE.findall(det_text)}
        untagged = matched - tagged
        assert not untagged, f"{name}: matches {untagged} without tagging them"


def test_tags_resolve_in_versioned_catalog(rules, catalog):
    known = set((catalog.get("techniques") or {}).keys())
    deprecated = set((catalog.get("deprecated") or {}).keys())
    for name, rule in rules.items():
        for tag in rule.get("tags") or []:
            if not TECH_TAG_RE.match(tag):
                continue
            tid = tag.split(".", 1)[1]
            assert tid not in deprecated, f"{name}: uses deprecated {tid}"
            assert tid in known, f"{name}: {tid} not in catalog v{catalog['version']}"


def test_catalog_wellformed(catalog):
    assert re.match(r"^\d{4}-\d{2}$", str(catalog.get("version", "")))
    for tid, entry in (catalog.get("techniques") or {}).items():
        assert TECH_ID_RE.match(tid), f"bad technique id {tid}"
        assert entry.get("name") and entry.get("d3fend"), f"{tid} incomplete"


# ---------------------------------------------------------------------------
# Embedded playbook scripts — placeholder substitution coverage
# ---------------------------------------------------------------------------


def test_all_script_placeholders_substituted():
    actions = WF_ACTIONS.read_text(encoding="utf-8")
    for script in sorted(SCRIPTS_DIR.glob("*.py")):
        placeholders = set(PLACEHOLDER_RE.findall(script.read_text(encoding="utf-8")))
        if not placeholders:
            continue
        for ph in placeholders:
            pat = r'\.replace\(\s*["\']?' + re.escape(ph)
            assert re.search(pat, actions), (
                f"{script.name}: {ph} never substituted in workflow_actions.py "
                "— the literal token ships to Shuffle"
            )


def test_containment_self_guards_on_decision():
    """Shuffle 2.2.1 branches never evaluate — the containment node IS the
    guard and must refuse non-'contain' decisions itself."""
    text = (SCRIPTS_DIR / "containment.py").read_text(encoding="utf-8")
    assert 'decision != "contain"' in text or "decision != 'contain'" in text


def test_workflow_definition_has_both_outcomes():
    """The graph must contain a containment path AND a false-positive path —
    a missing branch means one verdict class silently dead-ends."""
    actions = WF_ACTIONS.read_text(encoding="utf-8")
    for required in (
        "act_containment",
        "act_mark_false_positive",
        "act_notify_critical",
        "act_notify_info",
        "act_calc_mttr",
        "act_build_es_json",
    ):
        assert required in actions, f"missing node {required}"


def test_export_scripts_exist():
    assert EXPORT_CACAO.exists() and EXPORT_STIX.exists()


# ---------------------------------------------------------------------------
# Sigma metadata quality (DOM-EVAL-002)
# ---------------------------------------------------------------------------


def test_rules_have_falsepositives_and_references(rules):
    """Sigma quality fields: every rule must document its known-FP
    scenarios and cite its detection sources — a rule without them is a
    black box to its reviewers."""
    for name, rule in rules.items():
        fps = rule.get("falsepositives")
        assert isinstance(fps, list) and fps, f"{name}: no falsepositives list"
        refs = rule.get("references")
        assert isinstance(refs, list) and refs, f"{name}: no references list"
        for r in refs:
            assert str(r).startswith("https://"), f"{name}: bad reference {r!r}"


def test_references_cover_tagged_techniques(rules):
    """Every attack.tNNNN tag must be backed by its ATT&CK reference URL
    (sub-techniques map to /techniques/TXXXX/YYY/ paths)."""
    for name, rule in rules.items():
        refs = " ".join(str(r) for r in (rule.get("references") or []))
        for tag in rule.get("tags") or []:
            if not TECH_TAG_RE.match(tag):
                continue
            tid = tag.split(".", 1)[1].upper()
            base, _, sub = tid.partition(".")
            path = f"techniques/{base}/{sub}/" if sub else f"techniques/{base}/"
            assert path in refs, f"{name}: tag {tid} has no ATT&CK reference"


# ---------------------------------------------------------------------------
# Export validity — run the real exporters against committed sources
# (DOM-EVAL-003) so a broken exporter or drifted playbook fails the gate,
# not the next manual run.
# ---------------------------------------------------------------------------


def _load_module(path: Path, name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PLAYBOOKS = sorted((ROOT / "playbooks").glob("*.json"))


def test_playbook_jsons_wellformed():
    """Committed Shuffle exports must parse, carry the runtime graph
    (actions/branches), expose a start node, and the webhook-intake
    playbook must carry its trigger (the observe-only variant is invoked
    manually — zero triggers is legitimate there)."""
    import json

    assert len(PLAYBOOKS) >= 2, "playbook inventory shrank"
    for pb_path in PLAYBOOKS:
        d = json.loads(pb_path.read_text(encoding="utf-8"))
        assert d.get("actions"), f"{pb_path.name}: no actions"
        assert d.get("branches"), f"{pb_path.name}: no branches"
        assert "triggers" in d, f"{pb_path.name}: triggers key missing"
        assert any(a.get("isStartNode") for a in d["actions"]), (
            f"{pb_path.name}: no start node"
        )
        if "observeonly" not in pb_path.name:
            assert d["triggers"], f"{pb_path.name}: webhook trigger missing"


def test_playbook_contains_builder_actions():
    """Drift guard: every act_* node the builder actually instantiates
    must appear in the committed exports. The exports legitimately carry
    extra act_cortex_dyn_* nodes wired at runtime, so the check is
    builder ⊆ playbook, not equality. Ids only present as dead constants
    (e.g. legacy fused nodes) are not instantiation sites."""
    import json
    import re as _re

    src = WF_ACTIONS.read_text(encoding="utf-8")
    body = src.split("def build_actions", 1)[1]
    const_map = dict(_re.findall(r'(ACT_\w+)\s*=\s*"(act_\w+)"', src))
    instantiated = {
        const_map[tok] for tok in _re.findall(r"ACT_\w+", body) if tok in const_map
    } | set(_re.findall(r'act_[a-z0-9_]+', body))
    # The observe-only export intentionally drops the containment path —
    # that is its documented difference. Any OTHER missing node is drift.
    allowed_missing = {"act_containment"}
    for pb_path in PLAYBOOKS:
        d = json.loads(pb_path.read_text(encoding="utf-8"))
        pb_ids = {a["id"] for a in d["actions"]}
        missing = instantiated - pb_ids
        if "observeonly" in pb_path.name:
            missing -= allowed_missing
        assert not missing, f"{pb_path.name}: builder nodes absent from export: {missing}"


def test_cacao_export_is_spec_valid():
    """convert() on the committed playbook must yield a valid CACAO 2.0
    playbook — the exporter's own validator must return zero errors."""
    mod = _load_module(EXPORT_CACAO, "export_cacao")
    import json

    definition = json.loads(PLAYBOOKS[0].read_text(encoding="utf-8"))
    pb = mod.convert(definition)
    assert pb["type"] == "playbook" and pb["spec_version"] == "cacao-2.0"
    assert pb["workflow"], "empty workflow"
    errors = mod.validate_playbook(pb)
    assert not errors, f"CACAO validation: {errors}"


def test_stix_export_is_spec_valid():
    """build_bundle() must yield a structurally valid STIX 2.1 bundle."""
    mod = _load_module(EXPORT_STIX, "export_attack_stix")
    bundle = mod.build_bundle()
    errors = mod.validate_bundle(bundle)
    assert not errors, f"STIX validation: {errors}"
    assert bundle["type"] == "bundle"
    assert len(bundle["objects"]) > 50, "bundle suspiciously small"
