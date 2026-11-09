"""Unit tests for EVID-003 evidence quality scorer (score_evidence.py)."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "quality"))

import score_evidence


def _mk_package(
    root: Path,
    name: str,
    *,
    outcome: str = "passed",
    with_digest: bool = True,
    env: dict | None = None,
    evidence_files: tuple[str, ...] = ("docker_state.json",),
    tamper: bool = False,
) -> Path:
    pkg = root / name
    (pkg / "evidence").mkdir(parents=True)
    for fname in evidence_files + ("payload.json",):
        (pkg / "evidence" / fname).write_text('{"ok": true}', encoding="utf-8")
    artifacts = {}
    for f in (pkg / "evidence").iterdir():
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if tamper:
            digest = "0" * 64
        artifacts[f.name] = {"path": str(f), "sha256": digest} if with_digest else str(f)
    manifest = {
        "schema_version": "1.0",
        "test_name": name,
        "artifacts": artifacts,
        "correlation_id": f"e2e-{name}-x",
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    env = (
        env
        if env is not None
        else {
            "python": "3.11.9",
            "pytest": "9.0.3",
            "platform": "Linux",
            "git": {"commit": "abc123", "branch": "main", "dirty": False},
            "docker_images": {"soar_api": "sha256:dead"},
            "env_public": {"API_URL": "http://api:8000"},
        }
    )
    (pkg / "environment.json").write_text(json.dumps(env), encoding="utf-8")
    all_passed = outcome in ("passed", "skipped", "not_applicable")
    (pkg / "result.json").write_text(
        json.dumps(
            {
                "name": name,
                "outcome": outcome,
                "all_passed": all_passed,
                "passed": 3,
                "failed": 0,
                "total": 3,
            }
        ),
        encoding="utf-8",
    )
    (pkg / "assertions.json").write_text("[]", encoding="utf-8")
    (pkg / "cleanup.json").write_text('{"removed": []}', encoding="utf-8")
    return pkg


class TestPackageScoring:
    def test_full_e4_package_scores_high(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc01")
        res = score_evidence.score_package(pkg)
        assert res["score"] == 100.0
        assert res["tier"] == "E4"
        assert res["outcome"] == "passed"
        assert res["issues"] == []

    def test_tampered_digest_fails_integrity(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc02", tamper=True)
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["integrity"] == 0
        assert any("sha256 mismatch" in i for i in res["issues"])

    def test_missing_files_drop_completeness(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc03")
        (pkg / "cleanup.json").unlink()
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["completeness"] < 100

    def test_legacy_package_without_outcome_capped(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc04")
        result = json.loads((pkg / "result.json").read_text())
        del result["outcome"]
        (pkg / "result.json").write_text(json.dumps(result))
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["outcome"] == 50

    def test_skipped_with_all_passed_flagged(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc05", outcome="skipped")
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["outcome"] == 25

    def test_secret_env_key_fails_redaction(self, tmp_path):
        env = {
            "python": "3.11",
            "pytest": "9",
            "platform": "L",
            "git": {"commit": "x"},
            "docker_images": {"a": "b"},
            "env_public": {"THEHIVE_API_KEY": "abc"},
        }
        pkg = _mk_package(tmp_path, "tc06", env=env)
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["redaction"] == 0

    def test_bearer_token_in_artifact_fails_redaction(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc07")
        (pkg / "evidence" / "leak.json").write_text(
            json.dumps({"auth": "Bearer xyz123"}), encoding="utf-8"
        )
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["redaction"] == 0

    def test_missing_environment_scores_zero(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc08", env={"env_public": {}})
        res = score_evidence.score_package(pkg)
        assert res["dimensions"]["environment"] < 100

    def test_no_digests_blocks_e4_and_zeroes_integrity(self, tmp_path):
        pkg = _mk_package(tmp_path, "tc09", with_digest=False)
        res = score_evidence.score_package(pkg)
        # Observed-state evidence can still reach E3, but unanchored
        # artifacts can never substantiate E4 and integrity is 0.
        assert res["tier"] == "E3"
        assert res["dimensions"]["integrity"] == 0


class TestSummarize:
    def test_skipped_not_counted_as_passed(self, tmp_path):
        pkgs = [
            score_evidence.score_package(_mk_package(tmp_path, "a", outcome="passed")),
            score_evidence.score_package(_mk_package(tmp_path, "b", outcome="skipped")),
        ]
        summary = score_evidence.summarize(pkgs)
        assert summary["outcomes"]["skipped"] == 1
        # pass_rate counts only pass/fail/warning — skipped excluded.
        assert summary["pass_rate_counted"] == 1.0

    def test_confidence_interval_present(self, tmp_path):
        pkgs = [
            score_evidence.score_package(_mk_package(tmp_path, "a")),
            score_evidence.score_package(_mk_package(tmp_path, "b", tamper=True)),
        ]
        summary = score_evidence.summarize(pkgs)
        assert summary["score_ci95"] is not None
        assert "integrity failures present" in summary["gates_failed"]
        assert summary["verdict"] == "FAIL"

    def test_all_green_verdict_pass(self, tmp_path):
        pkgs = [score_evidence.score_package(_mk_package(tmp_path, n)) for n in ("a", "b", "c")]
        summary = score_evidence.summarize(pkgs)
        assert summary["verdict"] == "PASS"
        assert summary["tiers"]["E4"] == 3


class TestCli:
    def test_gate_fails_below_threshold(self, tmp_path, capsys):
        _mk_package(tmp_path, "low", tamper=True)
        rc = score_evidence.main(["--results", str(tmp_path), "--gate", "95"])
        assert rc == 1

    def test_gate_passes(self, tmp_path):
        _mk_package(tmp_path, "ok")
        out = tmp_path / "score.json"
        rc = score_evidence.main(["--results", str(tmp_path), "--out", str(out), "--gate", "50"])
        assert rc == 0
        assert json.loads(out.read_text())["summary"]["verdict"] == "PASS"

    def test_history_appends(self, tmp_path):
        _mk_package(tmp_path, "ok")
        hist = tmp_path / "hist.jsonl"
        score_evidence.main(["--results", str(tmp_path), "--history", str(hist)])
        score_evidence.main(["--results", str(tmp_path), "--history", str(hist)])
        assert len(hist.read_text().strip().splitlines()) == 2
