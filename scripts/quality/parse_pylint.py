"""Parse pylint output.

Runs pylint once with text format to get both the score and issues.
Parses the text output to extract the score line and count issues by
type. For detailed issue information, runs a second JSON pass only if
needed.
"""

import json
import re
import subprocess
import sys


def _extract_score(text: str) -> float | None:
    """Extract pylint score from text output."""
    match = re.search(r"rated at\s+([\d.]+)\s*/\s*10", text)
    if match:
        return float(match.group(1))
    return None


def _parse_text_issues(text: str) -> list[dict]:
    """Parse pylint text output into issue dicts.

    Pylint text format: module:line: type: symbol: message
    """
    issues = []
    for line in text.splitlines():
        # Match: module:line: type: symbol: message
        match = re.match(r"^(.+?):(\d+):\s*(\w+):\s*(.+?)\s*:\s*(.+)$", line)
        if match:
            module, lineno, itype, symbol, message = match.groups()
            if itype in ("error", "warning", "refactor", "convention", "info"):
                issues.append(
                    {
                        "type": itype,
                        "symbol": symbol,
                        "message": message[:200],
                        "module": module,
                        "line": int(lineno),
                    }
                )
    return issues


def parse(path: str = "src/") -> dict:
    """Run pylint and return structured results."""
    # Run with JSON for structured issues
    cmd_json = [
        sys.executable,
        "-m",
        "pylint",
        path,
        "--output-format=json",
        "--rcfile=pyproject.toml",
    ]
    result_json = subprocess.run(cmd_json, capture_output=True, text=True)
    try:
        issues = json.loads(result_json.stdout) if result_json.stdout.strip() else []
    except json.JSONDecodeError:
        issues = []

    # Run with text for score (quick — only need the summary)
    cmd_text = [
        sys.executable,
        "-m",
        "pylint",
        path,
        "--output-format=text",
        "--rcfile=pyproject.toml",
        "--score=y",
        "--reports=y",
        "--msg-template='{path}:{line}: {category}: {msg_id}: {msg}'",
    ]
    result_text = subprocess.run(cmd_text, capture_output=True, text=True)
    score = _extract_score(result_text.stdout) or _extract_score(result_text.stderr)

    by_type = {"error": 0, "warning": 0, "refactor": 0, "convention": 0, "info": 0}
    by_module: dict[str, int] = {}
    by_symbol: dict[str, int] = {}
    for issue in issues:
        t = issue.get("type", "info")
        by_type[t] = by_type.get(t, 0) + 1
        mod = issue.get("module", "?")
        by_module[mod] = by_module.get(mod, 0) + 1
        sym = issue.get("symbol", "?")
        by_symbol[sym] = by_symbol.get(sym, 0) + 1

    # Sort issues: errors first, then warnings
    priority = {"error": 0, "warning": 1, "refactor": 2, "convention": 3, "info": 4}
    sorted_issues = sorted(
        issues, key=lambda i: (priority.get(i.get("type", "info"), 5), i.get("line", 0))
    )

    # Ensure at least one example per symbol (for the report's example column)
    # Take one example per symbol first, then fill up with remaining issues.
    # This guarantees that every symbol in by_symbol has at least one
    # representative in the issues list.
    seen_syms: set[str] = set()
    examples: list[dict] = []
    remaining: list[dict] = []
    for i in sorted_issues:
        sym = i.get("symbol", "?")
        if sym not in seen_syms:
            seen_syms.add(sym)
            examples.append(i)
        else:
            remaining.append(i)
    # 50 total: one per symbol + fill with remaining (prioritized)
    curated = examples + remaining[: max(0, 50 - len(examples))]

    return {
        "score": score,
        "total_issues": len(issues),
        "by_type": by_type,
        "by_module": dict(sorted(by_module.items(), key=lambda x: -x[1])[:10]),
        "by_symbol": dict(sorted(by_symbol.items(), key=lambda x: -x[1])[:15]),
        "issues": [
            {
                "type": i.get("type", "?"),
                "symbol": i.get("symbol", "?"),
                "message": i.get("message", "")[:200],
                "module": i.get("module", "?"),
                "line": i.get("line", 0),
            }
            for i in curated[:50]
        ],
    }
