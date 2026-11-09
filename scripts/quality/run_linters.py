#!/usr/bin/env python3
"""Run every available linter and generate a consolidated report.

Usage:
    python scripts/quality/run_linters.py                 # run all, report only (never fails)
    python scripts/quality/run_linters.py --gate          # fail if a core linter fails
    python scripts/quality/run_linters.py --only ruff,mypy
    python scripts/quality/run_linters.py --skip pylint,semgrep

Outputs:
    reports/quality/lint-report.md   human-readable consolidated report
    reports/quality/lint-report.json machine-readable results
    reports/quality/lint/<tool>.log  raw output per tool

Core (gating) linters reproduce the historical `make lint` contract:
ruff, black, isort, flake8, mypy. Everything else is informational and
feeds the report. Tools that are not installed are reported as SKIP,
never as failures.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO_ROOT / "reports" / "quality"
LOG_DIR = OUT_DIR / "lint"

PY = sys.executable
SRC = ["src/", "tests/"]
SRC_ONLY = ["src/"]


# ---------------------------------------------------------------------------
# Result / parsing helpers
# ---------------------------------------------------------------------------


def _files_from_lines(output: str) -> Counter:
    """Extract ``path:line:...`` file names from classic linter output."""
    files: Counter = Counter()
    for line in output.splitlines():
        m = re.match(r"^([\w./\\-]+\.py)[:)]", line)
        if m:
            files[m.group(1)] += 1
    return files


def _codes_from_lines(output: str) -> Counter:
    """Extract rule codes like ``E501``/``F401``/``B008``/``W0612``."""
    codes: Counter = Counter()
    for line in output.splitlines():
        m = re.search(r"\b([A-Z]{1,4}\d{2,4})\b", line)
        if m:
            codes[m.group(1)] += 1
    return codes


def _count_lines(output: str, pattern: str = r"\.py:") -> int:
    return sum(1 for line in output.splitlines() if re.search(pattern, line))


def _json_output(result: dict):
    """Parse the captured stdout of a tool as JSON, tolerating noise."""
    raw = result.get("raw", "")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # some tools prefix log lines before the json blob
        m = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------------------
# Per-tool parsers  (result dict -> metrics/samples/files)
# ---------------------------------------------------------------------------


def parse_ruff(r: dict) -> dict:
    data = _json_output(r) or []
    codes: Counter = Counter()
    files: Counter = Counter()
    for item in data:
        codes[item.get("code") or "?"] += 1
        files[item.get("filename", "?")] += 1
    return {
        "issues": len(data),
        "top_codes": codes.most_common(10),
        "files": files.most_common(10),
        "samples": [
            f"{i.get('filename')}:{i.get('location', {}).get('row')} "
            f"{i.get('code')} {i.get('message', '')[:90]}"
            for i in data[:10]
        ],
    }


def parse_black(r: dict) -> dict:
    files = re.findall(r"would reformat (.+)", r["raw"])
    return {
        "issues": len(files),
        "files": Counter(files).most_common(10),
        "samples": [f"would reformat {f}" for f in files[:10]],
    }


def parse_isort(r: dict) -> dict:
    files = re.findall(r"ERROR:\s*(\S+)", r["raw"])
    return {
        "issues": len(files),
        "files": Counter(files).most_common(10),
        "samples": [f"unsorted imports: {f}" for f in files[:10]],
    }


def parse_generic_lines(r: dict) -> dict:
    n = _count_lines(r["raw"])
    files = _files_from_lines(r["raw"])
    codes = _codes_from_lines(r["raw"])
    samples = [l.strip()[:120] for l in r["raw"].splitlines() if ".py:" in l][:10]
    return {
        "issues": n,
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": samples,
    }


def parse_mypy(r: dict) -> dict:
    err_lines = [l for l in r["raw"].splitlines() if ": error:" in l]
    files: Counter = Counter()
    codes: Counter = Counter()
    for l in err_lines:
        m = re.match(r"^([\w./\\-]+\.py):\d+", l)
        if m:
            files[m.group(1)] += 1
        c = re.search(r"\[([\w-]+)\]\s*$", l)
        if c:
            codes[c.group(1)] += 1
    return {
        "issues": len(err_lines),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": err_lines[:10],
    }


def parse_pylint(r: dict) -> dict:
    data = _json_output(r) or []
    symbols: Counter = Counter()
    files: Counter = Counter()
    by_type: Counter = Counter()
    for m in data:
        symbols[m.get("symbol") or m.get("message-id") or "?"] += 1
        files[m.get("path", "?")] += 1
        by_type[m.get("type", "?")] += 1
    score_m = re.search(r"rated at ([\d.]+)/10", r["raw"])
    extra = {"score": float(score_m.group(1))} if score_m else {}
    return {
        "issues": len(data),
        "by_type": dict(by_type),
        "top_codes": symbols.most_common(10),
        "files": files.most_common(10),
        **extra,
        "samples": [
            f"{m.get('path')}:{m.get('line')} {m.get('symbol')} " f"{(m.get('message') or '')[:80]}"
            for m in data[:10]
        ],
    }


def parse_bandit(r: dict) -> dict:
    data = _json_output(r) or {}
    results = data.get("results", [])
    sev: Counter = Counter()
    files: Counter = Counter()
    for it in results:
        sev[it.get("issue_severity", "?")] += 1
        files[it.get("filename", "?")] += 1
    return {
        "issues": len(results),
        "severity": dict(sev),
        "files": files.most_common(10),
        "samples": [
            f"{i.get('filename')}:{i.get('line_number')} "
            f"{i.get('test_id')} [{i.get('issue_severity')}] "
            f"{(i.get('issue_text') or '')[:80]}"
            for i in results[:10]
        ],
    }


def parse_vulture(r: dict) -> dict:
    lines = [l for l in r["raw"].splitlines() if ".py:" in l]
    files = _files_from_lines(r["raw"])
    return {"issues": len(lines), "files": files.most_common(10), "samples": lines[:10]}


def parse_radon_cc(r: dict) -> dict:
    data = _json_output(r) or {}
    blocks, maxcc, total, worst = 0, 0, 0.0, Counter()
    grades: Counter = Counter()
    for fname, entries in data.items():
        for e in entries:
            blocks += 1
            cc = e.get("complexity", 0)
            total += cc
            maxcc = max(maxcc, cc)
            worst[fname] = max(worst[fname], cc)
            grades[e.get("rank", "?")] += 1
    return {
        "issues": sum(grades[g] for g in ("C", "D", "E", "F") if g in grades),
        "blocks": blocks,
        "avg": round(total / blocks, 2) if blocks else 0,
        "max": maxcc,
        "grades": dict(grades),
        "files": worst.most_common(10),
        "samples": [f"{f}: max CC {c}" for f, c in worst.most_common(10)],
    }


def parse_radon_mi(r: dict) -> dict:
    data = _json_output(r) or {}
    ranks: Counter = Counter()
    worst = []
    for f, e in data.items():
        ranks[e.get("rank", "?")] += 1
        worst.append((e.get("mi", 0), f))
    worst.sort()
    return {
        "issues": sum(ranks[g] for g in ("B", "C") if g in ranks),
        "ranks": dict(ranks),
        "avg_mi": round(sum(m for m, _ in worst) / len(worst), 1) if worst else 0,
        "files": [(f, m) for m, f in worst[:10]],
        "samples": [f"{f}: MI {m:.1f}" for m, f in worst[:10]],
    }


def parse_interrogate(r: dict) -> dict:
    m = re.search(r"actual:\s*([\d.]+)%", r["raw"])
    total = re.search(r"\|\s*TOTAL\s*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*(\d+)\s*\|", r["raw"])
    cov = float(m.group(1)) if m else 0.0
    return {
        "issues": 0 if cov >= 80 else 1,
        "coverage": cov,
        "covered": int(total.group(2)) if total else 0,
        "total": int(total.group(1)) if total else 0,
        "samples": [f"docstring coverage: {cov}%"],
    }


def parse_pip_audit(r: dict) -> dict:
    data = _json_output(r) or {}
    deps = data.get("dependencies", [])
    vulns = []
    for d in deps:
        for v in d.get("vulns", []):
            vulns.append(f"{d.get('name')} {d.get('version')}: {v.get('id')}")
    return {
        "issues": len(vulns),
        "samples": vulns[:10],
        "top_codes": Counter(v.split(":")[0].strip() for v in vulns).most_common(10),
    }


def parse_detect_secrets(r: dict) -> dict:
    data = _json_output(r) or {}
    results = data.get("results", {})
    total = sum(len(v) for v in results.values())
    return {
        "issues": total,
        "files": [(f, len(v)) for f, v in sorted(results.items(), key=lambda kv: -len(kv[1]))[:10]],
        "samples": [
            f"{f}: {len(v)} finding(s)"
            for f, v in sorted(results.items(), key=lambda kv: -len(kv[1]))[:10]
        ],
    }


def parse_semgrep(r: dict) -> dict:
    data = _json_output(r) or {}
    results = data.get("results", [])
    sev: Counter = Counter()
    files: Counter = Counter()
    for it in results:
        sev[it.get("extra", {}).get("severity", "?")] += 1
        files[it.get("path", "?")] += 1
    return {
        "issues": len(results),
        "severity": dict(sev),
        "files": files.most_common(10),
        "samples": [
            f"{i.get('path')}:{i.get('start', {}).get('line')} "
            f"{i.get('check_id', '?').split('.')[-1]}"
            for i in results[:10]
        ],
    }


def parse_markdownlint(r: dict) -> dict:
    lines = [l for l in r["raw"].splitlines() if ".md:" in l]
    files: Counter = Counter()
    codes: Counter = Counter()
    for l in lines:
        m = re.match(r"^([\w./\\-]+\.md):\d+", l)
        if m:
            files[m.group(1)] += 1
        c = re.search(r"\b(MD\d{3})\b", l)
        if c:
            codes[c.group(1)] += 1
    return {
        "issues": len(lines),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": lines[:10],
    }


def parse_pydoclint(r: dict) -> dict:
    """pydoclint prints files, then indented ``  line: DOCxxx: msg`` entries."""
    files: Counter = Counter()
    codes: Counter = Counter()
    samples = []
    current = "?"
    for l in r["raw"].splitlines():
        m = re.match(r"^\s+(\d+):\s*(DOC\d+):\s*(.*)", l)
        if m:
            files[current] += 1
            codes[m.group(2)] += 1
            if len(samples) < 10:
                samples.append(f"{current}:{m.group(1)} {m.group(2)} {m.group(3)[:80]}")
        elif re.match(r"^[\w./\\-]+\.py$", l.strip()):
            current = l.strip()
    return {
        "issues": sum(files.values()),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": samples,
    }


def parse_xenon(r: dict) -> dict:
    # xenon exits 0 when the code passes the complexity gates
    return {
        "issues": 0 if r["rc"] == 0 else 1,
        "samples": [l for l in r["raw"].splitlines() if l.strip()][:10] or ["within gates"],
    }


def parse_fawltydeps(r: dict) -> dict:
    data = _json_output(r) or {}
    und = data.get("undeclared_deps", []) or []
    unused = data.get("unused_deps", []) or []
    samples = []
    files: Counter = Counter()
    for dep in und[:10]:
        name = dep.get("name", "?")
        locs = ", ".join(
            f"{ref.get('path')}:{ref.get('lineno')}" for ref in dep.get("references", [])[:3]
        )
        samples.append(f"undeclared: {name} ({locs})")
        for ref in dep.get("references", []):
            files[ref.get("path", "?")] += 1
    for dep in unused[:10]:
        samples.append(f"unused: {dep.get('name', '?')}")
    return {
        "issues": len(und) + len(unused),
        "undeclared": len(und),
        "unused": len(unused),
        "files": files.most_common(10),
        "samples": samples or ["dependencies consistent"],
    }


def parse_codespell(r: dict) -> dict:
    lines = [l for l in r["raw"].splitlines() if "==>" in l]
    files: Counter = Counter()
    for l in lines:
        m = re.match(r"^([^:]+):", l)
        if m:
            files[m.group(1)] += 1
    return {
        "issues": len(lines),
        "files": files.most_common(10),
        "samples": [l.strip()[:120] for l in lines[:10]],
    }


def parse_yamllint(r: dict) -> dict:
    issues = 0
    files: Counter = Counter()
    codes: Counter = Counter()
    samples = []
    current = "?"
    for l in r["raw"].splitlines():
        if re.match(r"^\.?[\\/]?[\w./\\-]+\.(ya?ml)$", l.strip()):
            current = l.strip()
        elif re.match(r"^\s*\d+:\d+", l):
            issues += 1
            files[current] += 1
            c = re.search(r"\(([\w-]+)\)\s*$", l)
            if c:
                codes[c.group(1)] += 1
            if len(samples) < 10:
                samples.append(f"{current} {l.strip()[:100]}")
    return {
        "issues": issues,
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": samples,
    }


def parse_tryceratops(r: dict) -> dict:
    issues = 0
    files: Counter = Counter()
    codes: Counter = Counter()
    samples = []
    lines = r["raw"].splitlines()
    for i, l in enumerate(lines):
        m = re.match(r"^(.+\.py):(\d+):(\d+)", l.strip())
        if m:
            files[m.group(1)] += 1
        c = re.match(r"^\[(TRY\d+)\]\s*(.*)", l.strip())
        if c:
            issues += 1
            codes[c.group(1)] += 1
            prev = lines[i - 1].strip() if i else ""
            samples.append(f"{prev} {c.group(1)} {c.group(2)[:80]}".strip()[:120])
    return {
        "issues": issues,
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": samples[:10],
    }


def parse_refurb(r: dict) -> dict:
    lines = [
        l for l in r["raw"].splitlines() if re.match(r"^.+\.py:\d+:\d+:?\s*\[?FURB", l.strip())
    ]
    files = _files_from_lines(r["raw"])
    codes = Counter()
    for l in lines:
        c = re.search(r"(FURB\d+)", l)
        if c:
            codes[c.group(1)] += 1
    return {
        "issues": len(lines),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": [l.strip()[:120] for l in lines[:10]],
    }


def parse_eradicate(r: dict) -> dict:
    removed = [l for l in r["raw"].splitlines() if l.startswith("-#")]
    files = Counter(
        m.group(1) for l in r["raw"].splitlines() if (m := re.match(r"^--- before/(.+)", l))
    )
    return {
        "issues": len(removed),
        "files": files.most_common(10),
        "samples": [l.strip()[:110] for l in removed[:10]],
    }


def parse_pydocstyle(r: dict) -> dict:
    lines = [l for l in r["raw"].splitlines() if re.search(r"\bD\d{3}\b", l)]
    files = _files_from_lines(r["raw"])
    codes = Counter()
    for l in lines:
        c = re.search(r"\b(D\d{3})\b", l)
        if c:
            codes[c.group(1)] += 1
    return {
        "issues": len(lines),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": [l.strip()[:120] for l in lines[:10]],
    }


def parse_checkov(r: dict) -> dict:
    # checkov emits a stream of concatenated JSON objects (one per scanned
    # directory), not a JSON array — decode them one by one.
    blocks = []
    decoder = json.JSONDecoder()
    raw = r["raw"].strip()
    pos = 0
    while pos < len(raw):
        try:
            obj, end = decoder.raw_decode(raw, pos)
        except json.JSONDecodeError:
            nxt = raw.find("{", pos + 1)
            if nxt < 0:
                break
            pos = nxt
            continue
        if isinstance(obj, dict):
            blocks.append(obj)
        pos = end
        while pos < len(raw) and raw[pos] not in "[{":
            pos += 1
    failed = []
    for block in blocks:
        failed.extend((block.get("results") or {}).get("failed_checks", []) or [])
    codes = Counter(f.get("check_id", "?") for f in failed)
    files = Counter(f.get("file_path", "?") for f in failed)
    return {
        "issues": len(failed),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": [
            f"{f.get('file_path')}:{f.get('file_line_range', ['?'])[0]} "
            f"{f.get('check_id')} {f.get('check_name', '')[:70]}"
            for f in failed[:10]
        ],
    }


def parse_gcc_style(r: dict) -> dict:
    """shellcheck -f gcc / hadolint style: ``file:line:col: severity: msg``."""
    lines = [
        l
        for l in r["raw"].splitlines()
        if re.match(r"^[\w./\\-]+:\d+:\d+?:\s*(error|warning|info|note|style)", l.strip())
        or re.match(r"^[\w./\\-]+:\d+\s+\w+\d+\s+(error|warning|info)", l.strip())
    ]
    files: Counter = Counter()
    codes: Counter = Counter()
    for l in lines:
        m = re.match(r"^([\w./\\-]+):\d+", l.strip())
        if m:
            files[m.group(1)] += 1
        c = re.search(r"\b((?:SC|DL)\d+)\b", l)
        if c:
            codes[c.group(1)] += 1
    return {
        "issues": len(lines),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": [l.strip()[:120] for l in lines[:10]],
    }


def parse_actionlint(r: dict) -> dict:
    lines = [l for l in r["raw"].splitlines() if re.match(r"^.+\.ya?ml:\d+:\d+:", l.strip())]
    files: Counter = Counter()
    codes: Counter = Counter()
    for l in lines:
        m = re.match(r"^([\w./\\-]+):\d+", l.strip())
        if m:
            files[m.group(1)] += 1
        c = re.search(r"\[([\w-]+)\]\s*$", l)
        if c:
            codes[c.group(1)] += 1
    return {
        "issues": len(lines),
        "files": files.most_common(10),
        "top_codes": codes.most_common(10),
        "samples": [l.strip()[:120] for l in lines[:10]],
    }


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


def _t(
    name,
    category,
    cmd,
    parser,
    *,
    core=False,
    binary=None,
    module=None,
    docker=False,
    env=None,
    timeout=180,
    rc_ok=(0,),
):
    return {
        "name": name,
        "category": category,
        "cmd": cmd,
        "parser": parser,
        "core": core,
        "binary": binary,
        "module": module,
        "docker": docker,
        "env": env,
        "timeout": timeout,
        "rc_ok": rc_ok,
    }


# ---------------------------------------------------------------------------
# Dynamic file lists for tools that take explicit paths
# ---------------------------------------------------------------------------

_VENDOR_DIRS = {
    ".git",
    ".idea",
    "node_modules",
    "artifacts",
    "runtime",
    "backups",
    "build",
    "dist",
    "reports",
    "__pycache__",
    ".venv",
    "venv",
}


def _repo_files(*patterns: str) -> list[str]:
    out = []
    for pat in patterns:
        for p in REPO_ROOT.rglob(pat):
            if not any(part in _VENDOR_DIRS for part in p.parts):
                out.append(str(p.relative_to(REPO_ROOT)).replace("\\", "/"))
    return sorted(set(out))


def _shellcheck_cmd() -> list[str]:
    files = _repo_files("*.sh")
    return ["shellcheck", "-f", "gcc", *files] if files else []


def _hadolint_cmd() -> list[str]:
    files = _repo_files("Dockerfile", "*.Dockerfile")
    if not files:
        return []
    root = REPO_ROOT.as_posix()
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{root}:/repo",
        "-w",
        "/repo",
        "hadolint/hadolint:v2.12.0-debian",
        "hadolint",
        *files,
    ]


def _actionlint_cmd() -> list[str]:
    if not (REPO_ROOT / ".github" / "workflows").is_dir():
        return []
    root = REPO_ROOT.as_posix()
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{root}:/repo",
        "-w",
        "/repo",
        "rhysd/actionlint:1.7.7",
        "-oneline",
    ]


def _checkov_cmd() -> list[str]:
    root = REPO_ROOT.as_posix()
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{root}:/repo",
        "-w",
        "/repo",
        "bridgecrew/checkov:latest",
        "--config-file",
        ".checkov.yaml",
        "-o",
        "json",
    ]


TOOLS = [
    # -- core gates (historical `make lint` contract) -----------------------
    _t(
        "ruff",
        "logic",
        [PY, "-m", "ruff", "check", *SRC, "scripts/setup/", "--output-format", "json"],
        parse_ruff,
        core=True,
        rc_ok=(0, 1),
    ),
    _t("black", "style", [PY, "-m", "black", "--check", *SRC], parse_black, core=True),
    _t("isort", "style", [PY, "-m", "isort", "--check-only", *SRC], parse_isort, core=True),
    _t("flake8", "style", [PY, "-m", "flake8", *SRC], parse_generic_lines, core=True),
    _t(
        "mypy",
        "types",
        [PY, "-m", "mypy", *SRC_ONLY, "--no-color-output"],
        parse_mypy,
        core=True,
        timeout=600,
    ),
    # -- informational linters ---------------------------------------------
    _t(
        "pylint",
        "logic",
        [PY, "-m", "pylint", *SRC_ONLY, "--output-format", "json", "--score", "n"],
        parse_pylint,
        timeout=600,
        rc_ok=(0, 1, 4, 8, 16, 32),
    ),
    _t("pyflakes", "logic", [PY, "-m", "pyflakes", *SRC], parse_generic_lines),
    _t(
        "pycodestyle",
        "style",
        [PY, "-m", "pycodestyle", "--max-line-length", "100", *SRC],
        parse_generic_lines,
    ),
    _t(
        "pydoclint",
        "docs",
        ["pydoclint", *SRC_ONLY],
        parse_pydoclint,
        binary="pydoclint",
        rc_ok=(0, 1, 2),
    ),
    _t(
        "bandit",
        "security",
        [PY, "-m", "bandit", "--ini", ".bandit", "-r", *SRC_ONLY, "-f", "json", "-q"],
        parse_bandit,
        rc_ok=(0, 1),
    ),
    _t(
        "vulture",
        "dead-code",
        [PY, "-m", "vulture", "src/soar_lab", "--min-confidence", "80"],
        parse_vulture,
    ),
    _t(
        "radon-cc",
        "complexity",
        [PY, "-m", "radon", "cc", *SRC_ONLY, "-j"],
        parse_radon_cc,
        rc_ok=(0, 1),
    ),
    _t(
        "radon-mi",
        "complexity",
        [PY, "-m", "radon", "mi", *SRC_ONLY, "-j"],
        parse_radon_mi,
        rc_ok=(0, 1),
    ),
    _t(
        "xenon",
        "complexity",
        [
            PY,
            "-m",
            "xenon",
            "--max-absolute",
            "C",
            "--max-modules",
            "C",
            "--max-average",
            "B",
            *SRC_ONLY,
        ],
        parse_xenon,
    ),
    _t(
        "interrogate",
        "docs",
        [PY, "-m", "interrogate", "-v", *SRC_ONLY],
        parse_interrogate,
        rc_ok=(0, 1, 2),
    ),
    _t(
        "mccabe",
        "complexity",
        [PY, "-m", "mccabe", "--min", "10", *SRC_ONLY],
        parse_generic_lines,
        rc_ok=(0, 1),
    ),
    _t(
        "detect-secrets",
        "security",
        [PY, "-m", "detect_secrets", "scan", *SRC_ONLY],
        parse_detect_secrets,
        rc_ok=(0, 1),
    ),
    _t(
        "pip-audit",
        "security",
        [PY, "-m", "pip_audit", "--format", "json", "-r", "requirements.lock"],
        parse_pip_audit,
        timeout=300,
        rc_ok=(0, 1),
    ),
    _t(
        "semgrep",
        "security",
        [
            "semgrep",
            "scan",
            "--config",
            "p/python",
            "--json",
            "--quiet",
            "--metrics",
            "off",
            *SRC_ONLY,
        ],
        parse_semgrep,
        binary="semgrep",
        timeout=300,
        rc_ok=(0, 1, 2),
    ),
    _t(
        "markdownlint",
        "docs",
        ["markdownlint", "docs/"],
        parse_markdownlint,
        binary="markdownlint",
        rc_ok=(0, 1),
    ),
    # -- extended suite ----------------------------------------------------
    _t(
        "fawltydeps",
        "deps",
        [PY, "-m", "fawltydeps", "--json"],
        parse_fawltydeps,
        module="fawltydeps",
        timeout=300,
        rc_ok=(0, 2, 3, 4),
    ),
    _t(
        "codespell",
        "spelling",
        ["codespell"],
        parse_codespell,
        binary="codespell",
        rc_ok=(0, 1, 2),
    ),
    _t(
        "yamllint",
        "yaml",
        [PY, "-m", "yamllint", "."],
        parse_yamllint,
        module="yamllint",
        timeout=300,
        rc_ok=(0, 1, 2),
    ),
    _t(
        "tryceratops",
        "logic",
        [PY, "-m", "tryceratops", *SRC_ONLY],
        parse_tryceratops,
        module="tryceratops",
        rc_ok=(0, 1),
    ),
    _t(
        "refurb",
        "logic",
        ["refurb", *SRC],
        parse_refurb,
        binary="refurb",
        rc_ok=(0, 1),
    ),
    _t(
        "eradicate",
        "dead-code",
        [PY, "-m", "eradicate", "--recursive", "src/", "tests/", "scripts/"],
        parse_eradicate,
        module="eradicate",
        env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        rc_ok=(0, 1),
    ),
    _t(
        "pydocstyle",
        "docs",
        ["pydocstyle", *SRC],
        parse_pydocstyle,
        binary="pydocstyle",
        rc_ok=(0, 1, 2),
    ),
    _t(
        "checkov",
        "iac",
        _checkov_cmd,
        parse_checkov,
        docker=True,
        timeout=300,
        rc_ok=(0,),
    ),
    _t(
        "shellcheck",
        "shell",
        _shellcheck_cmd,
        parse_gcc_style,
        binary="shellcheck",
        rc_ok=(0, 1),
    ),
    _t(
        "hadolint",
        "iac",
        _hadolint_cmd,
        parse_gcc_style,
        docker=True,
        timeout=300,
        rc_ok=(0, 1),
    ),
    _t(
        "actionlint",
        "iac",
        _actionlint_cmd,
        parse_actionlint,
        docker=True,
        timeout=300,
        rc_ok=(0, 1, 2, 3),
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _skip(tool: dict, reason: str) -> dict:
    return {
        "name": tool["name"],
        "category": tool["category"],
        "status": "SKIP",
        "reason": reason,
        "issues": 0,
        "time": 0.0,
    }


def _docker_available() -> bool:
    try:
        return (
            subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                timeout=20,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_tool(tool: dict) -> dict:
    name = tool["name"]
    cmd = tool["cmd"]() if callable(tool["cmd"]) else list(tool["cmd"])
    if not cmd:
        return _skip(tool, "no files to lint")
    if tool["module"]:
        import importlib.util

        if importlib.util.find_spec(tool["module"]) is None:
            return _skip(tool, f"module '{tool['module']}' not installed")
    if tool["docker"]:
        if not _docker_available():
            return _skip(tool, "docker daemon unavailable")
    if tool["binary"]:
        resolved = shutil.which(tool["binary"])
        if not resolved:
            return _skip(tool, f"'{tool['binary']}' not installed")
        if not os.path.splitext(resolved)[1]:
            # bare shim (e.g. pipx/uv entry point) — prefer the exec'able
            # sibling so subprocess works without a shell.
            for ext in (".exe", ".cmd", ".bat"):
                if os.path.exists(resolved + ext):
                    resolved += ext
                    break
        cmd = [resolved, *cmd[1:]]
        if resolved.lower().endswith((".cmd", ".bat")):
            # batch shims cannot be exec'd directly on Windows
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", resolved, *cmd[1:]]
    env = {**os.environ, **tool["env"]} if tool["env"] else None
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=tool["timeout"],
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        raw = (proc.stdout or "") + (proc.stderr or "")
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "category": tool["category"],
            "status": "TIMEOUT",
            "issues": 0,
            "time": tool["timeout"],
            "samples": [],
            "reason": f"exceeded {tool['timeout']}s",
        }
    except FileNotFoundError:
        return {
            "name": name,
            "category": tool["category"],
            "status": "SKIP",
            "reason": "executable not found",
            "issues": 0,
            "time": 0.0,
        }
    except OSError as exc:
        return {
            "name": name,
            "category": tool["category"],
            "status": "ERROR",
            "reason": f"cannot execute: {exc}",
            "issues": 0,
            "time": 0.0,
        }
    elapsed = round(time.time() - t0, 1)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / f"{name}.log").write_text(raw[:200_000], encoding="utf-8")

    res = {"name": name, "category": tool["category"], "rc": rc, "raw": raw, "time": elapsed}
    try:
        parsed = tool["parser"](res)
    except Exception as exc:  # a broken parser must not kill the run
        parsed = {"issues": -1, "samples": [f"parse error: {exc}"]}
    res.update(parsed)
    res.pop("raw")

    crashed = rc not in tool["rc_ok"] and parsed.get("issues", 0) in (0, -1)
    if crashed:
        res["status"] = "ERROR"
        res["reason"] = (
            f"exit {rc}: {raw.splitlines()[-1][:120] if raw.splitlines() else 'no output'}"
        )
    elif parsed.get("issues", 0) > 0:
        res["status"] = "FAIL" if tool["core"] else "WARN"
    else:
        res["status"] = "PASS"
    res["core"] = tool["core"]
    return res


def _git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️", "ERROR": "💥", "TIMEOUT": "⏱️"}
CONSOLE_ICON = {
    "PASS": "[OK]",
    "WARN": "[WARN]",
    "FAIL": "[FAIL]",
    "SKIP": "[SKIP]",
    "ERROR": "[ERR]",
    "TIMEOUT": "[TO]",
}


def build_markdown(results: list[dict], duration: float) -> str:
    sha = _git_sha()
    n_pass = sum(r["status"] == "PASS" for r in results)
    n_warn = sum(r["status"] == "WARN" for r in results)
    n_fail = sum(r["status"] == "FAIL" for r in results)
    n_skip = sum(r["status"] == "SKIP" for r in results)
    n_err = sum(r["status"] in ("ERROR", "TIMEOUT") for r in results)
    total_issues = sum(max(r.get("issues", 0), 0) for r in results)
    core_fail = [r["name"] for r in results if r.get("core") and r["status"] == "FAIL"]

    # cross-tool worst files — normalize separators + make repo-relative
    root = str(REPO_ROOT).replace("\\", "/")

    def _norm(f: str) -> str:
        f = f.replace("\\", "/")
        return f[len(root) + 1 :] if f.startswith(root) else f

    file_hits: Counter = Counter()
    file_issues: Counter = Counter()
    for r in results:
        for f, c in r.get("files", []) or []:
            if isinstance(f, str):
                f = _norm(f)
                file_hits[f] += 1
                file_issues[f] += c if isinstance(c, int) else 1

    md = [
        "# Lint Report — SOAR Ransomware Lab",
        "",
        f"- **Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Commit**: `{sha}`",
        "- **Scope**: `src/`, `tests/` (+ `scripts/setup/` for ruff)",
        f"- **Duration**: {duration:.0f}s · **Tools run**: {len(results)}",
        "",
        "## Verdict",
        "",
        f"{'❌ **FAIL** — core linters failing: ' + ', '.join(f'`{c}`' for c in core_fail) if core_fail else '✅ **PASS** — all core gates green'}",
        "",
        "| ✅ pass | ⚠️ warn | ❌ fail | ⏭️ skip | 💥 error | total issues |",
        "|---|---|---|---|---|---|",
        f"| {n_pass} | {n_warn} | {n_fail} | {n_skip} | {n_err} | {total_issues} |",
        "",
        "## Summary by tool",
        "",
        "| Category | Tool | Status | Issues | Time | Detail |",
        "|---|---|---|---|---|---|",
    ]
    order = {"core": 0}
    for r in sorted(
        results,
        key=lambda x: (order.get("core" if x.get("core") else "", 1), x["category"], x["name"]),
    ):
        detail = ""
        if r["status"] in ("SKIP", "ERROR", "TIMEOUT"):
            detail = r.get("reason", "")
        elif r.get("top_codes"):
            detail = ", ".join(f"`{c}`×{n}" for c, n in r["top_codes"][:4])
        elif r.get("severity"):
            detail = ", ".join(f"{k}:{v}" for k, v in r["severity"].items())
        elif "coverage" in r:
            detail = f"docstring coverage {r['coverage']}%"
        elif "avg" in r:
            detail = f"avg CC {r['avg']}, max {r['max']}"
        elif "avg_mi" in r:
            detail = f"avg MI {r['avg_mi']}"
        elif "score" in r:
            detail = f"score {r['score']}/10"
        core = " 🔒" if r.get("core") else ""
        md.append(
            f"| {r['category']} | `{r['name']}`{core} | {ICON[r['status']]} "
            f"{r['status']} | {max(r.get('issues', 0), 0)} | {r['time']}s | {detail} |"
        )

    md += ["", "🔒 = core gate (blocks `make lint`)"]

    # actionable recommendations derived from actual findings
    recs = []
    by_name = {r["name"]: r for r in results}
    if by_name.get("black", {}).get("issues") or by_name.get("isort", {}).get("issues"):
        recs.append(
            "- Run `make lint-fix` — auto-fixes black + isort + ruff "
            f"({sum(max(by_name.get(t, {}).get('issues', 0), 0) for t in ('black', 'isort', 'ruff'))} findings)"
        )
    if by_name.get("radon-cc", {}).get("issues"):
        recs.append(
            f"- Refactor {by_name['radon-cc']['issues']} functions with CC ≥ C "
            "(see radon-cc worst files below)"
        )
    if by_name.get("detect-secrets", {}).get("issues"):
        recs.append("- Triage `detect-secrets` findings — real secrets must move to `.env.full`")
    if by_name.get("pip-audit", {}).get("issues"):
        recs.append("- Review `pip-audit` vulnerabilities — bump or pin affected packages")
    if by_name.get("semgrep", {}).get("issues"):
        recs.append("- Review `semgrep` security findings (taint/injection rules)")
    if by_name.get("markdownlint", {}).get("issues"):
        recs.append("- `markdownlint docs/ --fix` fixes most doc style issues automatically")
    if recs:
        md += ["", "## Recommended actions", "", *recs]

    md += [
        "",
        "## Worst files (flagged by most tools)",
        "",
        "| File | Tools flagging | Total findings |",
        "|---|---|---|",
    ]
    for f, hits in file_hits.most_common(15):
        md.append(f"| `{f}` | {hits} | {file_issues[f]} |")

    md += ["", "## Per-tool findings", ""]
    for r in results:
        if r["status"] == "SKIP":
            continue
        md.append(
            f"### {ICON[r['status']]} {r['name']} — {r['status']} "
            f"({max(r.get('issues', 0), 0)} findings)"
        )
        md.append("")
        if r.get("by_type"):
            md.append(f"- message types: `{r['by_type']}`")
        if r.get("grades"):
            md.append(f"- complexity grades: `{r['grades']}`")
        if r.get("ranks"):
            md.append(f"- MI ranks: `{r['ranks']}`")
        samples = (r.get("samples") or [])[:10]
        if samples:
            root = str(REPO_ROOT)
            md.append("```")
            md.extend(
                str(s).replace(root + "\\", "").replace(root + "/", "")[:160] for s in samples
            )
            md.append("```")
        md.append(f"- raw log: `reports/quality/lint/{r['name']}.log`")
        md.append("")
    md += [
        "---",
        "*Generated by `scripts/quality/run_linters.py` — "
        "raw logs in `reports/quality/lint/`, machine data in `lint-report.json`*",
    ]
    return "\n".join(md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Run all linters and build a report")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="exit 1 if any core linter (ruff/black/isort/flake8/mypy) fails",
    )
    ap.add_argument("--only", help="comma-separated subset of tools to run")
    ap.add_argument("--skip", help="comma-separated tools to skip")
    ap.add_argument("--output-dir", default=str(OUT_DIR))
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else None
    skip = set(args.skip.split(",")) if args.skip else set()
    tools = [t for t in TOOLS if (only is None or t["name"] in only) and t["name"] not in skip]

    print("=" * 70)
    print(f"SOAR Lab — Lint suite ({len(tools)} tools)")
    print("=" * 70)

    results = []
    t0 = time.time()
    for tool in tools:
        core = " [core]" if tool["core"] else ""
        print(f"  > {tool['name']}{core} ...", end="", flush=True)
        r = run_tool(tool)
        print(
            f" {CONSOLE_ICON[r['status']]} {r['status']} "
            f"({max(r.get('issues', 0), 0)} findings, {r['time']}s)"
        )
        results.append(r)
    duration = time.time() - t0

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lint-report.json").write_text(
        json.dumps(
            {
                "generated": datetime.now(UTC).isoformat(),
                "duration_s": round(duration, 1),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    md = build_markdown(results, duration)
    (out_dir / "lint-report.md").write_text(md, encoding="utf-8")

    core_fail = [r["name"] for r in results if r.get("core") and r["status"] == "FAIL"]
    print("=" * 70)
    print(f"Report: {out_dir / 'lint-report.md'}")
    if core_fail:
        print(f"CORE GATE FAILED: {', '.join(core_fail)}")
    else:
        print("Core gates: all green")
    print("=" * 70)
    return 1 if (args.gate and core_fail) else 0


if __name__ == "__main__":
    sys.exit(main())
