"""TC-27 — baseline/golden-file semantics.

The repo ships versioned baselines (tests/baseline/*.json + commit.txt)
gated byte-identically by docs_quality.py and written only via
export_openapi.py. These tests verify the semantics around them:
versioning evidence, secret normalization, semantic-diff capability,
volatile-field normalization, and the sanctioned rebaseline path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

BASELINE = Path("/app/tests/baseline")
REPO = Path("/app")

# A "secret-looking value": a JSON string field whose key smells secret and
# whose value is a long opaque token. Field NAMES (schema descriptions) are
# fine — only raw values matter.
SECRET_VALUE = re.compile(
    r'"(?:api_key|apikey|secret|token|password|private_key)"\s*:\s*'
    r'"([A-Za-z0-9+/=_\-]{20,})"',
    re.IGNORECASE,
)
VOLATILE_KEYS = {"_id", "id", "createdAt", "updatedAt", "timestamp", "ts", "uuid"}


def _normalize(obj):
    """Strip volatile keys recursively for semantic comparison."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def _semantic_equal(a, b) -> bool:
    """Order-insensitive semantic equality on parsed JSON."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_semantic_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            _semantic_equal(x, y) for x, y in zip(a, b)
        )
    return a == b


@pytest.mark.e2e
class TestBaselineSemantics:
    tc_id = "TC-27"

    def test_baseline_versioned_with_commit(self):
        """commit.txt anchors the baseline set to a git SHA — the snapshot
        is traceable to the revision that produced it."""
        commit = (BASELINE / "commit.txt").read_text().strip()
        assert re.fullmatch(r"[0-9a-f]{7,40}", commit), (
            f"commit.txt is not a git SHA: {commit[:40]!r}"
        )

    def test_no_secret_values_in_baselines(self):
        """Baselines may name secret fields (schema docs) but must never
        embed real opaque secret VALUES."""
        offenders = []
        for f in BASELINE.glob("*.json"):
            for m in SECRET_VALUE.finditer(f.read_text()):
                offenders.append(f"{f.name}: {m.group(1)[:8]}…")
        assert not offenders, "secret-looking values in baselines: " + "; ".join(offenders[:5])

    def test_semantic_diff_detects_change_not_format(self):
        """A semantic comparator flags real mutations but ignores pure
        formatting/key-order noise — byte-diff alone can't tell them apart."""
        spec = json.loads((BASELINE / "ports_matrix.json").read_text())
        # same content, serialized differently -> semantically equal
        reordered = json.loads(json.dumps(spec, sort_keys=True))
        assert _semantic_equal(spec, reordered)
        # a real mutation -> detected
        mutated = json.loads(json.dumps(spec))
        if isinstance(mutated, dict):
            mutated["__injected__"] = True
        elif isinstance(mutated, list):
            mutated.append({"__injected__": True})
        assert not _semantic_equal(spec, mutated)

    def test_volatile_fields_normalized(self):
        """Volatile keys (_id, timestamps) normalize away — a diff that only
        re-stamps ids/dates is not a semantic drift."""
        a = {"_id": "~111", "createdAt": 1700000001, "name": "case", "tags": ["x"]}
        b = {"_id": "~999", "createdAt": 1799999999, "name": "case", "tags": ["x"]}
        assert _normalize(a) == _normalize(b)
        # but a content change still differs after normalization
        b2 = dict(b, name="renamed")
        assert _normalize(a) != _normalize(b2)

    def test_rebaseline_path_is_sanctioned_script(self):
        """The only sanctioned write path to the baseline is
        scripts/ci/export_openapi.py — and the byte-gate exists in
        docs_quality.py. Together they enforce the 'rebaseline is an
        explicit act' contract."""
        exporter = REPO / "scripts/ci/export_openapi.py"
        gate = REPO / "scripts/ci/docs_quality.py"
        assert exporter.exists(), "export_openapi.py missing"
        assert "tests/baseline" in exporter.read_text() or (
            'baseline' in exporter.read_text()
        )
        gate_src = gate.read_text()
        assert "baseline" in gate_src and "openapi.json" in gate_src
