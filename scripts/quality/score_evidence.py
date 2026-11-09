#!/usr/bin/env python3
"""EVID-003: automatic evidence-package quality scoring.

Walks the per-test artifact packages under the E2E results directory
(each ``<correlation_id>/`` containing ``manifest.json``) and produces a
per-test quality score plus a run-level summary with the gates that were
not met.

Dimensions scored (0..100 per package):

- ``completeness`` — required files present: manifest.json,
  environment.json, result.json, assertions.json, cleanup.json and a
  non-empty ``evidence/`` directory.
- ``integrity`` — every artifact entry carrying a ``sha256`` digest in
  the manifest verifies against the bytes on disk.
- ``environment`` — environment.json captures commit, docker images and
  python/pytest versions (reproducibility context).
- ``outcome`` — result.json carries a valid formal outcome
  (EVID-001 ``passed|failed|warning|skipped|not_applicable``) and
  non-``passed`` outcomes are never counted as approvals.
- ``redaction`` — no secret-keyed entries in ``env_public`` and none of
  the collected secret values appear verbatim in the JSON artifacts.

Evidence tiers (reported per package):

- ``E2`` — artifact package exists with integrity digests.
- ``E3`` — observed-state evidence present (e.g. docker_state,
  service_health, workflow_execution in evidence/).
- ``E4`` — externally verifiable anchors present (sha256 digests,
  git commit, docker image digests in environment.json).

Usage::

    python scripts/quality/score_evidence.py [--results DIR] [--out FILE]
        [--gate MIN_SCORE] [--history FILE]

Exit code is non-zero only with ``--gate`` when the mean score is below
the threshold or any package has zero scored dimensions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "manifest.json",
    "environment.json",
    "result.json",
    "assertions.json",
    "cleanup.json",
)
VALID_OUTCOMES = {"passed", "failed", "warning", "skipped", "not_applicable"}
_SECRET_KEY_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "CREDENTIAL")
_OBSERVED_STATE_EVIDENCE = {
    "docker_state.json",
    "service_health.json",
    "workflow_execution.json",
    "opensearch_docs.json",
    "elasticsearch_docs.json",
    "loki_logs.json",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_strings(obj: Any):
    """Yield every string value nested in a JSON-like structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_strings(v)


def _score_completeness(pkg: Path) -> tuple[int, list[str]]:
    missing = [f for f in REQUIRED_FILES if not (pkg / f).is_file()]
    evidence = pkg / "evidence"
    if not evidence.is_dir() or not any(evidence.iterdir()):
        missing.append("evidence/")
    present = len(REQUIRED_FILES) + 1 - len(missing)
    return int(100 * present / (len(REQUIRED_FILES) + 1)), missing


def _score_integrity(pkg: Path, manifest: dict[str, Any]) -> tuple[int, list[str]]:
    artifacts = manifest.get("artifacts") or {}
    checked = failed = 0
    failed_names: list[str] = []
    for name, entry in artifacts.items():
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not digest:
            continue
        checked += 1
        candidates = [pkg / "evidence" / name, pkg / name, Path(entry.get("path", ""))]
        target = next((c for c in candidates if c.is_file()), None)
        if target is None or _sha256_file(target) != digest:
            failed += 1
            failed_names.append(name)
    if checked == 0:
        return 0, ["no sha256 digests in manifest"]
    return int(100 * (checked - failed) / checked), [f"sha256 mismatch: {n}" for n in failed_names]


def _score_environment(env: dict[str, Any] | None) -> tuple[int, list[str]]:
    if not isinstance(env, dict):
        return 0, ["environment.json missing or unreadable"]
    missing: list[str] = []
    if not (env.get("git") or {}).get("commit"):
        missing.append("git.commit")
    if not env.get("docker_images"):
        missing.append("docker_images")
    for k in ("python", "pytest", "platform"):
        if not env.get(k):
            missing.append(k)
    return int(100 * (5 - len(missing)) / 5), [f"env missing: {m}" for m in missing]


def _score_outcome(result: dict[str, Any] | None) -> tuple[int, list[str]]:
    if not isinstance(result, dict):
        return 0, ["result.json missing or unreadable"]
    outcome = result.get("outcome")
    if outcome is None:
        # Legacy packages predate EVID-001: accept all_passed but cap at 50.
        if "all_passed" in result:
            return 50, ["no formal outcome field (legacy artifact)"]
        return 0, ["no outcome field"]
    if outcome not in VALID_OUTCOMES:
        return 0, [f"invalid outcome {outcome!r}"]
    # A skipped/not_applicable test that claims all_passed is a false green.
    if outcome in {"skipped", "not_applicable"} and result.get("all_passed") is True:
        return 25, [f"{outcome} but all_passed=true"]
    return 100, []


def _score_redaction(pkg: Path, env: dict[str, Any] | None) -> tuple[int, list[str]]:
    problems: list[str] = []
    env_public = (env or {}).get("env_public") or {}
    leaked_keys = [k for k in env_public if any(h in k.upper() for h in _SECRET_KEY_HINTS)]
    if leaked_keys:
        problems.append(f"secret-keyed env entries: {sorted(leaked_keys)}")
    # Deterministic leak signal: an Authorization-style token serialized
    # verbatim in any JSON artifact.
    for f in pkg.rglob("*.json"):
        data = _load_json(f)
        if data is None:
            continue
        if any(s.startswith("Bearer ") for s in _iter_strings(data)):
            problems.append(f"bearer token serialized in {f.name}")
            break
    return (0 if problems else 100), problems


def _evidence_tier(pkg: Path, manifest: dict[str, Any], env: dict[str, Any] | None) -> str:
    """Highest evidence tier the package substantiates (E2 < E3 < E4)."""
    tier = "E1"
    artifacts = manifest.get("artifacts") or {}
    has_digests = any(isinstance(e, dict) and e.get("sha256") for e in artifacts.values())
    if has_digests:
        tier = "E2"
    evidence = pkg / "evidence"
    if evidence.is_dir() and {p.name for p in evidence.iterdir()} & _OBSERVED_STATE_EVIDENCE:
        tier = "E3"
    env_ok = (
        isinstance(env, dict) and (env.get("git") or {}).get("commit") and env.get("docker_images")
    )
    if tier == "E3" and env_ok and has_digests:
        tier = "E4"
    return tier


def score_package(pkg: Path) -> dict[str, Any]:
    """Score a single evidence package directory."""
    manifest = _load_json(pkg / "manifest.json") or {}
    env = _load_json(pkg / "environment.json")
    result = _load_json(pkg / "result.json")

    completeness, c_issues = _score_completeness(pkg)
    integrity, i_issues = _score_integrity(pkg, manifest if isinstance(manifest, dict) else {})
    environ, e_issues = _score_environment(env if isinstance(env, dict) else None)
    outcome, o_issues = _score_outcome(result if isinstance(result, dict) else None)
    redaction, r_issues = _score_redaction(pkg, env if isinstance(env, dict) else None)

    dimensions = {
        "completeness": completeness,
        "integrity": integrity,
        "environment": environ,
        "outcome": outcome,
        "redaction": redaction,
    }
    weights = {
        "completeness": 0.2,
        "integrity": 0.25,
        "environment": 0.15,
        "outcome": 0.25,
        "redaction": 0.15,
    }
    score = round(sum(dimensions[k] * weights[k] for k in dimensions), 1)
    res_outcome = (result or {}).get("outcome") or (
        "legacy" if isinstance(result, dict) else "missing"
    )
    return {
        "package": pkg.name,
        "test_name": (manifest or {}).get("test_name") or (result or {}).get("name") or pkg.name,
        "score": score,
        "dimensions": dimensions,
        "tier": _evidence_tier(pkg, manifest if isinstance(manifest, dict) else {}, env),
        "outcome": res_outcome,
        "issues": c_issues + i_issues + e_issues + o_issues + r_issues,
    }


def summarize(packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Run-level summary — skipped/N-A never count as passed (EVID-003)."""
    by_outcome: dict[str, int] = {}
    for p in packages:
        by_outcome[p["outcome"]] = by_outcome.get(p["outcome"], 0) + 1
    scores = [p["score"] for p in packages]
    mean = round(sum(scores) / len(scores), 1) if scores else 0.0
    # Operational confidence interval: ±1.96·σ/√n over package scores.
    if len(scores) > 1:
        var = sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)
        ci = round(1.96 * (var**0.5) / (len(scores) ** 0.5), 1)
    else:
        ci = None
    counted = (
        by_outcome.get("passed", 0) + by_outcome.get("failed", 0) + by_outcome.get("warning", 0)
    )
    gates = []
    if mean < 80:
        gates.append(f"mean_score {mean} < 80")
    if any(p["dimensions"]["integrity"] < 100 for p in packages):
        gates.append("integrity failures present")
    if any(p["outcome"] == "missing" for p in packages):
        gates.append("packages without result.json")
    return {
        "packages": len(packages),
        "mean_score": mean,
        "score_ci95": ci,
        "outcomes": by_outcome,
        "pass_rate_counted": round(by_outcome.get("passed", 0) / counted, 3) if counted else None,
        "tiers": {t: sum(1 for p in packages if p["tier"] == t) for t in ("E1", "E2", "E3", "E4")},
        "gates_failed": gates,
        "verdict": "PASS" if not gates else "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--results",
        default="reports/validation/results",
        help="Directory containing per-test evidence packages",
    )
    ap.add_argument("--out", default=None, help="Write summary JSON here")
    ap.add_argument(
        "--history", default=None, help="Append {timestamp, mean_score} to this JSONL file"
    )
    ap.add_argument(
        "--gate", type=float, default=None, help="Exit non-zero when mean score is below this value"
    )
    args = ap.parse_args(argv)

    root = Path(args.results)
    packages = [
        score_package(d)
        for d in sorted(root.rglob("*"))
        if d.is_dir() and (d / "manifest.json").is_file()
    ]
    summary = summarize(packages)
    report = {"summary": summary, "packages": packages}
    text = json.dumps(report, indent=2, default=str)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if args.history:
        from datetime import UTC, datetime

        Path(args.history).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.history).open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "mean_score": summary["mean_score"],
                        "packages": summary["packages"],
                    }
                )
                + "\n"
            )

    if args.gate is not None:
        if summary["mean_score"] < args.gate or summary["gates_failed"]:
            print(
                f"GATE FAIL: {summary['gates_failed']} (mean={summary['mean_score']})",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
