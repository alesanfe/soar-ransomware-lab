"""Parse radon output for complexity, maintainability, Halstead, and raw
metrics."""

import json
import subprocess
import sys


def run_radon(command: str, path: str = "src/") -> dict:
    """Run a radon subcommand and return parsed JSON."""
    cmd = [sys.executable, "-m", "radon", command, path, "-j"]
    if command == "mi":
        cmd = [sys.executable, "-m", "radon", command, path, "-s", "-j"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        return {"error": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"Failed to parse radon {command} output", "raw": result.stdout[:500]}


def parse_complexity(path: str = "src/") -> dict:
    """Parse cyclomatic complexity (radon cc).

    Returns {filepath: [blocks]}.
    """
    return run_radon("cc", path)


def parse_maintainability(path: str = "src/") -> dict:
    """Parse maintainability index (radon mi).

    Returns {filepath: mi_score}.
    """
    return run_radon("mi", path)


def parse_halstead(path: str = "src/") -> dict:
    """Parse Halstead metrics (radon hal).

    Returns {filepath: [metrics]}.
    """
    return run_radon("hal", path)


def parse_raw(path: str = "src/") -> dict:
    """Parse raw metrics (radon raw).

    Returns {filepath: {loc, lloc, sloc, ...}}.
    """
    return run_radon("raw", path)


def get_complexity_summary(path: str = "src/") -> dict:
    """Get aggregated complexity summary."""
    data = parse_complexity(path)
    if "error" in data:
        return data
    all_blocks = []
    for filepath, blocks in data.items():
        for b in blocks:
            if not isinstance(b, dict):
                continue
            b["filepath"] = filepath
            all_blocks.append(b)
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    max_cx = 0
    total_cx = 0
    for b in all_blocks:
        g = b.get("rank", "A")
        c = b.get("complexity", 0)
        grades[g] = grades.get(g, 0) + 1
        total_cx += c
        max_cx = max(max_cx, c)
    avg = total_cx / len(all_blocks) if all_blocks else 0
    hotspots = sorted(all_blocks, key=lambda x: -x.get("complexity", 0))[:10]
    return {
        "total_blocks": len(all_blocks),
        "average_complexity": round(avg, 2),
        "max_complexity": max_cx,
        "grade_distribution": grades,
        "hotspots": [
            {
                "name": h.get("name", "?"),
                "filepath": h.get("filepath", "?"),
                "complexity": h.get("complexity", 0),
                "rank": h.get("rank", "?"),
                "line": h.get("lineno", 0),
            }
            for h in hotspots
        ],
    }


def get_maintainability_summary(path: str = "src/") -> dict:
    """Get aggregated maintainability summary."""
    data = parse_maintainability(path)
    if "error" in data:
        return data
    scores = []
    for filepath, score in data.items():
        if isinstance(score, (int, float)):
            scores.append((filepath, score))
        elif isinstance(score, dict) and "mi" in score:
            scores.append((filepath, score["mi"]))
    if not scores:
        return {"error": "No maintainability scores found"}
    scores.sort(key=lambda x: x[1])
    avg = sum(s for _, s in scores) / len(scores)
    return {
        "total_files": len(scores),
        "average_mi": round(avg, 2),
        "min_mi": round(scores[0][1], 2),
        "max_mi": round(scores[-1][1], 2),
        "worst_files": [{"filepath": f, "mi": round(s, 2)} for f, s in scores[:10]],
    }
