"""Parse ruff linting output."""

import json
import subprocess
import sys


def parse(path: str = "src/") -> dict:
    """Run ruff check and return structured results.

    Uses the project's ruff configuration (pyproject.toml) instead of
    overriding with --select, to avoid false positives from rules that
    are intentionally disabled in the project config.
    """
    cmd = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        path,
        "--output-format",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return {"total_errors": 0, "errors": [], "by_rule": {}, "by_file": {}}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Failed to parse ruff output", "raw": result.stdout[:500]}
    by_rule: dict[str, int] = {}
    by_file: dict[str, int] = {}
    for item in data:
        rule = item.get("code", "unknown")
        filepath = item.get("filename", "?")
        by_rule[rule] = by_rule.get(rule, 0) + 1
        by_file[filepath] = by_file.get(filepath, 0) + 1
    return {
        "total_errors": len(data),
        "errors": data[:50],
        "by_rule": dict(sorted(by_rule.items(), key=lambda x: -x[1])),
        "by_file": dict(sorted(by_file.items(), key=lambda x: -x[1])[:10]),
    }


def check_format(path: str = "src/") -> dict:
    """Run ruff format --check and return results."""
    cmd = [sys.executable, "-m", "ruff", "format", "--check", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    would_change = []
    if result.returncode != 0:
        for line in result.stdout.splitlines():
            if line.strip():
                would_change.append(line.strip())
    return {
        "formatted": result.returncode == 0,
        "would_reformat": would_change[:20],
        "count": len(would_change),
    }
