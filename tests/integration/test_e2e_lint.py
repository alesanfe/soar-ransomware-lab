"""E2E-LINT-001: permanent AST lint guard for the E2E suite.

Enforces the anti-pattern rules from ``docs/18-e2e-suite-backlog-9of10.md``
(swallowed asserts, test-calls-test, ``max(caseId)`` selection, except:pass,
fixed IDs, ``EXECUTING``-as-success, vacuous bounds, arbitrary sleeps, …)
via a *ratchet*: the current finding set is compared against
``tests/e2e/oracle_baseline.json`` — any finding NOT in the baseline fails.

Regenerate the baseline after fixing oracles:

    python scripts/quality/e2e_oracle_audit.py \\
        --baseline tests/e2e/oracle_baseline.json --write-baseline
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.quality import e2e_oracle_audit as audit

E2E_ROOT = ROOT / "tests" / "e2e"
BASELINE = E2E_ROOT / "oracle_baseline.json"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def reports():
    return audit.scan(E2E_ROOT)


def test_e2e_lint_no_new_violations(reports):
    """No finding may exist that is not in the accepted baseline."""
    accepted = audit.load_baseline(BASELINE)
    assert accepted, (
        f"baseline empty or missing at {BASELINE} — run: "
        "python scripts/quality/e2e_oracle_audit.py --baseline "
        "tests/e2e/oracle_baseline.json --write-baseline"
    )
    new = [f for r in reports for f in r.findings if audit.finding_fingerprint(f) not in accepted]
    assert (
        not new
    ), f"{len(new)} NEW E2E oracle anti-pattern(s) — fix or extend baseline:\n" + "\n".join(
        f"  {f.file}:{f.line} [{f.category}] {f.function}: {f.snippet[:80]}" for f in new[:25]
    )


def test_e2e_lint_baseline_not_stale(reports):
    """Report (don't fail) how many baseline fingerprints are already fixed —
    a shrinking backlog is the point; regenerate the baseline periodically."""
    accepted = audit.load_baseline(BASELINE)
    current = {audit.finding_fingerprint(f) for r in reports for f in r.findings}
    stale = accepted - current
    # Informational assertion: keep the baseline within 25% of live findings —
    # a heavily stale baseline means it was not regenerated after cleanups.
    assert len(stale) <= max(len(current), len(accepted)) * 0.25, (
        f"{len(stale)}/{len(accepted)} baseline fingerprints no longer exist "
        "in the code — regenerate tests/e2e/oracle_baseline.json"
    )


def test_e2e_lint_scanner_self_check(reports):
    """Sanity: the scan itself must see the suite (guards silent skips)."""
    assert len(reports) >= 40, "scanner saw <40 e2e files — root path drift?"
    assert sum(r.assertions for r in reports) > 500
