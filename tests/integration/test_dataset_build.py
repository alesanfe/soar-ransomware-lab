"""EXP-01: the publishable dataset must be deterministic, schema-valid and
fully anonymized (no real IPs, domains, hostnames or malware hashes)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "maintenance" / "build_dataset.py"
DATASET = ROOT / "datasets" / "soar-ransomware-alerts-v1.jsonl"
MANIFEST = ROOT / "datasets" / "MANIFEST.json"

sys.path.insert(0, str(ROOT / "scripts" / "maintenance"))
import build_dataset

_REQUIRED_FIELDS = {
    "alert_id",
    "alert_type",
    "event_type",
    "severity",
    "hostname",
    "src_ip",
    "hash",
    "source",
    "detection_time",
    "description",
    "expected_verdict",
    "expected_pipeline_outcome",
}
_DOC_NETS = ("192.0.2.", "198.51.100.", "203.0.113.")


def _records() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]


class TestDeterminism:
    def test_same_seed_same_bytes(self, tmp_path: Path):
        recs = build_dataset.build_dataset(70, 30, 20261108)
        body = "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs)
        recs2 = build_dataset.build_dataset(70, 30, 20261108)
        body2 = "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs2)
        assert body == body2

    def test_different_seed_differs(self):
        assert build_dataset.build_dataset(70, 30, 1) != build_dataset.build_dataset(70, 30, 2)

    def test_manifest_sha256_matches_file(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        actual = hashlib.sha256(DATASET.read_bytes()).hexdigest()
        assert actual == manifest["jsonl_sha256"], (
            "committed dataset drifted from MANIFEST — regenerate with "
            "scripts/maintenance/build_dataset.py"
        )

    def test_cli_reproduces_published_bytes(self, tmp_path: Path):
        out = tmp_path / "ds.jsonl"
        subprocess.run(
            [sys.executable, str(SCRIPT), "--out", str(out)],
            check=True,
            capture_output=True,
        )
        assert out.read_bytes() == DATASET.read_bytes()


class TestSchema:
    def test_all_records_have_required_fields(self):
        for rec in _records():
            missing = _REQUIRED_FIELDS - rec.keys()
            assert not missing, f"{rec.get('alert_id')}: missing {missing}"

    def test_counts_and_verdicts(self):
        recs = _records()
        mal = [r for r in recs if r["expected_verdict"] == "malicious"]
        ben = [r for r in recs if r["expected_verdict"] == "benign"]
        assert len(mal) == 70 and len(ben) == 30
        assert all(r["severity"] >= 2 for r in mal)
        assert all(r["severity"] == 1 for r in ben)

    def test_loadable_by_pipeline_loader(self):
        from soar_lab.simulator.dataset_replay import load_dataset

        assert len(list(load_dataset(DATASET))) == 100


class TestAnonymization:
    def test_no_real_ips(self):
        for rec in _records():
            assert rec["src_ip"].startswith(_DOC_NETS)
            for ip in rec.get("c2_ips", []):
                assert ip.startswith(_DOC_NETS)

    def test_domains_are_reserved_example(self):
        for rec in _records():
            domain = rec.get("domain")
            if domain:
                assert domain.endswith(".soar-dataset.example.com")
            url = rec.get("url")
            if url:
                assert ".soar-dataset.example.com" in url

    def test_hostnames_are_lab_synthetic(self):
        for rec in _records():
            assert rec["hostname"].startswith(("ws-lab-", "srv-lab-"))

    def test_source_marks_dataset_origin(self):
        for rec in _records():
            assert rec["source"] == "soar-dataset-v1"

    def test_hashes_are_synthetic(self):
        # Synthetic hashes are sha256(seed, family, i) — verify one matches.
        rec = next(r for r in _records() if r["expected_verdict"] == "malicious")
        i = int(rec["alert_id"].split("-")[-1])
        expected = hashlib.sha256(f"20261108|{rec['malware_family']}|{i}".encode()).hexdigest()
        assert rec["hash"] == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
