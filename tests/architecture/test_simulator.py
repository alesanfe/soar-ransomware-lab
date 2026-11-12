"""Architecture gates — alert simulator (eval 42).

Static invariants for ``src/soar_lab/simulator/`` documented in
``docs/42-eval-simulator.md``: every embedded IoC hash must satisfy the
domain hash contract (32/40/64 hex), the package must be importable, and
transient 5xx responses must be retried.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "src" / "soar_lab" / "simulator" / "simulate_alerts.py"
SIM_PKG = ROOT / "src" / "soar_lab" / "simulator" / "__init__.py"
REPLAY = ROOT / "src" / "soar_lab" / "simulator" / "dataset_replay.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_simulator_is_a_package():
    assert SIM_PKG.exists(), "simulator/ lacks __init__.py — namespace-package accident"


def test_all_embedded_hashes_satisfy_domain_contract():
    """SIM-EVAL-001 regression: every ``"hash": "…"`` literal must be 32/40/64 hex."""
    bad = []
    for m in re.finditer(r'"hash":\s*"([0-9a-fA-F]+)"', _read(SIM)):
        if len(m.group(1)) not in (32, 40, 64):
            bad.append(m.group(1)[:16])
    assert not bad, f"simulator hashes violate HashValidator contract: {bad}"


def test_generator_always_sets_domain_field():
    """GoogleDNS analyzer contract — alerts must always carry a domain."""
    src = _read(SIM)
    assert 'alert["domain"]' in src
    assert "c2_domains" in src


def test_send_alert_retries_all_transient_5xx():
    src = _read(SIM)
    assert "resp.status_code >= 500" in src, "retry narrowed to a single status code"


def test_webhook_resolution_has_no_hardcoded_fallback():
    src = _read(SIM)
    assert "SHUFFLE_WEBHOOK_URL" in src and "webhook_info.json" in src
    assert not re.search(r'return\s+"http://\d', src), "hardcoded webhook URL leaked back in"


def test_replay_supports_limit_delay_and_result_callback():
    src = _read(REPLAY)
    for param in ("limit", "delay", "on_result", "sleep", "tag"):
        assert param in src, f"replay_dataset lost {param} injection point"


def test_replay_counts_success_rate_safely():
    src = _read(REPLAY)
    assert "if total else 0.0" in src or "if total" in src, "zero-division guard missing"


# --- SIM-EVAL-2 (eval 61): ATT&CK technique↔tactic coherence ------------------

# Canonical ATT&CK tactic membership for every technique the simulator
# emits (ATT&CK Enterprise v14). A family's declared ``tactics`` must
# cover every emitted technique — emitting T1021.004 while declaring
# only "Impact" mislabels the alert's kill-chain stage.
ATTACK_TECH_TACTICS: dict[str, set[str]] = {
    "T1003": {"Credential Access"},
    "T1018": {"Discovery"},
    "T1021.001": {"Lateral Movement"},
    "T1021.004": {"Lateral Movement"},
    "T1027": {"Defense Evasion"},
    "T1041": {"Exfiltration"},
    "T1046": {"Discovery"},
    "T1056.001": {"Collection", "Credential Access"},
    "T1059": {"Execution"},
    "T1059.001": {"Execution"},
    "T1059.003": {"Execution"},
    "T1068": {"Privilege Escalation"},
    "T1078": {"Defense Evasion", "Persistence", "Privilege Escalation", "Initial Access"},
    "T1098": {"Persistence", "Privilege Escalation"},
    "T1102": {"Command and Control"},
    "T1110.003": {"Credential Access"},
    "T1133": {"Persistence", "Initial Access"},
    "T1136": {"Persistence"},
    "T1190": {"Initial Access"},
    "T1219": {"Command and Control"},
    "T1480.001": {"Defense Evasion", "Execution"},
    "T1486": {"Impact"},
    "T1491": {"Impact"},
    "T1491.001": {"Impact"},
    "T1539": {"Credential Access"},
    "T1547.001": {"Persistence", "Privilege Escalation"},
    "T1556.006": {"Credential Access", "Defense Evasion"},
    "T1562.001": {"Defense Evasion"},
    "T1563": {"Lateral Movement"},
    "T1566.001": {"Initial Access"},
    "T1566.002": {"Initial Access"},
    "T1567": {"Exfiltration"},
    "T1567.002": {"Exfiltration"},
    "T1572": {"Command and Control"},
}


def _family_blocks():
    """Yield (name, techniques, tactics) for every family dict and stage."""
    src = _read(SIM)
    pattern = re.compile(
        r'"(?:name|stage)":\s*"([^"]+)".*?"techniques":\s*\[([^\]]+)\]'
        r'.*?"tactics":\s*\[([^\]]+)\]',
        re.S,
    )
    for m in pattern.finditer(src):
        techs = re.findall(r'"(T\d{4}(?:\.\d{3})?)"', m.group(2))
        tactics = set(re.findall(r'"([^"]+)"', m.group(3)))
        yield m.group(1), techs, tactics


def test_emitted_techniques_are_canonical_attack_ids():
    blocks = list(_family_blocks())
    assert len(blocks) >= 20, f"extractor matched {len(blocks)} blocks — regex drifted?"
    unknown = []
    for name, techs, _ in blocks:
        for t in techs:
            if t not in ATTACK_TECH_TACTICS:
                unknown.append(f"{name}:{t}")
    assert not unknown, f"technique IDs not in ATT&CK map (typo or update map): {unknown}"


def test_technique_tactic_coherence():
    """SIM-EVAL-2-001: every emitted technique must be reachable through
    one of the family's declared tactics (ATT&CK fidelity)."""
    incoherent = []
    for name, techs, tactics in _family_blocks():
        for t in techs:
            canon = ATTACK_TECH_TACTICS.get(t, set())
            if canon and not (canon & tactics):
                incoherent.append(f"{name}:{t} needs {sorted(canon)}, has {sorted(tactics)}")
    assert not incoherent, "tactic lists incomplete vs emitted techniques: " + "; ".join(incoherent)
