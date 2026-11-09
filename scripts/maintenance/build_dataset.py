#!/usr/bin/env python3
"""Build the publishable, anonymized SOAR ransomware alert dataset (EXP-01).

Generates a deterministic JSONL dataset of labeled alerts with the same
schema the live simulator uses, but with every environment-specific or
third-party value replaced by documentation ranges:

- ``src_ip``        -> RFC 5737 TEST-NET-1/2/3 addresses only
- ``hostname``      -> ``ws-lab-XX`` / ``srv-lab-XX`` lab hostnames
- ``domain``/``url``-> ``*.soar-dataset.example.com`` (RFC 2606 reserved TLD)
- ``hash``          -> deterministic synthetic SHA-256 (never a real sample)
- ``c2_ips``        -> TEST-NET only
- ``detection_time``-> deterministic offset from a fixed epoch

Determinism: ``--seed`` fixes every pseudo-random choice, so the same
command produces byte-identical output. ``MANIFEST.json`` records the
SHA-256 of the JSONL as the reproducibility anchor a third party can
verify after re-running this script.

Each record carries ground truth (``expected_verdict``,
``expected_pipeline_outcome``) so replay runs can be scored without
access to the lab's internal verdict logic.

Usage:
    python scripts/maintenance/build_dataset.py \
        --out datasets/soar-ransomware-alerts-v1.jsonl \
        --malicious 70 --benign 30 --seed 20261108
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
DATASET_SOURCE = "soar-dataset-v1"
_FIXED_EPOCH = "2026-01-01T00:00:00Z"

# RFC 5737 documentation ranges — publishable by definition.
_TEST_NETS = ("192.0.2", "198.51.100", "203.0.113")

# Synthetic ransomware families (names only — hashes are generated).
_MALICIOUS_FAMILIES = [
    {
        "name": "Lockbit",
        "process": "lockbit.exe",
        "severity": 4,
        "techniques": ["T1486", "T1490"],
        "tactics": ["Impact"],
    },
    {
        "name": "BlackCat",
        "process": "alphv.exe",
        "severity": 4,
        "techniques": ["T1486", "T1041"],
        "tactics": ["Impact", "Exfiltration"],
    },
    {
        "name": "Royal",
        "process": "royal.exe",
        "severity": 3,
        "techniques": ["T1486", "T1059"],
        "tactics": ["Impact", "Execution"],
    },
    {
        "name": "Play",
        "process": "play.exe",
        "severity": 3,
        "techniques": ["T1486"],
        "tactics": ["Impact"],
    },
    {
        "name": "Akira",
        "process": "akira.exe",
        "severity": 3,
        "techniques": ["T1486", "T1567"],
        "tactics": ["Impact", "Exfiltration"],
    },
    {
        "name": "Phobos",
        "process": "phobos.exe",
        "severity": 3,
        "techniques": ["T1486", "T1021"],
        "tactics": ["Impact", "Lateral Movement"],
    },
]

_RANSOM_STAGES = [
    {
        "stage": "encryption",
        "event_type": "ransomware_detection",
        "process": "encryptor.exe",
        "severity": 2,
        "techniques": ["T1486", "T1059"],
        "tactics": ["Impact", "Execution"],
    },
    {
        "stage": "exfiltration",
        "event_type": "data_exfiltration",
        "process": "exfil.exe",
        "severity": 3,
        "techniques": ["T1041", "T1567"],
        "tactics": ["Exfiltration"],
    },
    {
        "stage": "ransom_note",
        "event_type": "ransomware_detection",
        "process": "ransom_note.txt",
        "severity": 3,
        "techniques": ["T1486"],
        "tactics": ["Impact"],
    },
]

_BENIGN_SOURCES = [
    {"process": "svchost.exe", "event_type": "file_monitoring"},
    {"process": "explorer.exe", "event_type": "file_monitoring"},
    {"process": "chrome.exe", "event_type": "process_execution"},
    {"process": "Teams.exe", "event_type": "process_execution"},
    {"process": "WindowsUpdate.exe", "event_type": "file_monitoring"},
    {"process": "OneDrive.exe", "event_type": "file_monitoring"},
]


def _synthetic_sha256(*parts: object) -> str:
    """Deterministic fake SHA-256 — never a real malware sample."""
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def _test_net_ip(rng: random.Random) -> str:
    return f"{rng.choice(_TEST_NETS)}.{rng.randint(2, 254)}"


def _hostname(rng: random.Random, i: int) -> str:
    prefix = "srv" if rng.random() < 0.25 else "ws"
    return f"{prefix}-lab-{i % 60:02d}"


def _detection_time(i: int) -> str:
    # Deterministic: epoch + i*5 minutes, rendered as ISO.
    minutes = i * 5
    hh, mm = (minutes // 60) % 24, minutes % 60
    day = 1 + minutes // (24 * 60)
    return f"2026-01-{day:02d}T{hh:02d}:{mm:02d}:00Z"


def _malicious_alert(rng: random.Random, i: int, seed: int) -> dict[str, Any]:
    fam = rng.choice(_MALICIOUS_FAMILIES)
    hostname = _hostname(rng, i)
    if rng.random() < 0.2:
        stage = rng.choice(_RANSOM_STAGES)
        event_type, process = stage["event_type"], stage["process"]
        severity, techniques, tactics = (stage["severity"], stage["techniques"], stage["tactics"])
    else:
        event_type, process = "ransomware_detection", fam["process"]
        severity, techniques, tactics = fam["severity"], fam["techniques"], fam["tactics"]

    alert: dict[str, Any] = {
        "alert_id": f"DS-MAL-{i:04d}",
        "alert_type": "ransomware",
        "event_type": event_type,
        "severity": severity,
        "hostname": hostname,
        "src_ip": _test_net_ip(rng),
        "hash": _synthetic_sha256(seed, fam["name"], i),
        "source": DATASET_SOURCE,
        "detection_time": _detection_time(i),
        "description": f"Ransomware {fam['name']} detectado en {hostname}",
        "process_name": process,
        "mitre_techniques": techniques,
        "mitre_tactics": tactics,
        "malware_family": fam["name"],
        "domain": f"{fam['name'].lower()}.soar-dataset.example.com",
        "expected_verdict": "malicious",
        "expected_pipeline_outcome": "case_created",
    }
    if rng.random() < 0.30:
        alert["url"] = (
            f"https://{fam['name'].lower()}.soar-dataset.example.com/"
            f"payload/{_synthetic_sha256(seed, 'url', i)[:12]}"
        )
    if rng.random() < 0.15:
        alert["c2_ips"] = [_test_net_ip(rng) for _ in range(rng.randint(1, 3))]
    if rng.random() < 0.10:
        alert["file_path"] = f"C:\\ProgramData\\{fam['name']}\\{process}"
    return alert


def _benign_alert(rng: random.Random, i: int, seed: int) -> dict[str, Any]:
    src = rng.choice(_BENIGN_SOURCES)
    hostname = _hostname(rng, i)
    return {
        "alert_id": f"DS-BEN-{i:04d}",
        "alert_type": "ransomware",
        "event_type": src["event_type"],
        "severity": 1,
        "hostname": hostname,
        "src_ip": _test_net_ip(rng),
        "hash": _synthetic_sha256(seed, "benign", src["process"], i),
        "source": DATASET_SOURCE,
        "detection_time": _detection_time(i),
        "description": f"Actividad legítima {src['process']} en {hostname}",
        "process_name": src["process"],
        "confidence": 20,
        "expected_verdict": "benign",
        "expected_pipeline_outcome": "no_case_or_false_positive",
    }


def build_dataset(malicious: int, benign: int, seed: int) -> list[dict[str, Any]]:
    """Build the deterministic, anonymized alert list."""
    rng = random.Random(seed)
    records = [_malicious_alert(rng, i, seed) for i in range(malicious)] + [
        _benign_alert(rng, i, seed) for i in range(benign)
    ]
    # Deterministic interleaving so replays exercise both classes early.
    rng.shuffle(records)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="datasets/soar-ransomware-alerts-v1.jsonl")
    parser.add_argument("--malicious", type=int, default=70)
    parser.add_argument("--benign", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()

    records = build_dataset(args.malicious, args.benign, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    # Byte-exact write: CRLF translation would break the recorded sha256
    # on Windows — the MANIFEST hash must match the on-disk bytes.
    out.write_bytes(body.encode("utf-8"))

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset": out.name,
        "seed": args.seed,
        "counts": {
            "malicious": args.malicious,
            "benign": args.benign,
            "total": len(records),
        },
        "jsonl_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "generated_by": "scripts/maintenance/build_dataset.py",
        "fixed_epoch": _FIXED_EPOCH,
        "anonymization": {
            "src_ip": "RFC 5737 TEST-NET-1/2/3",
            "domain": "*.soar-dataset.example.com (RFC 2606)",
            "hash": "synthetic sha256(seed, family, index)",
            "hostname": "ws-lab-*/srv-lab-*",
        },
        "reproduce": (
            f"python scripts/maintenance/build_dataset.py --out {out} "
            f"--malicious {args.malicious} --benign {args.benign} --seed {args.seed}"
        ),
    }
    manifest_path = out.parent / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Dataset: {out} ({len(records)} records, sha256={manifest['jsonl_sha256'][:16]}…)")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
