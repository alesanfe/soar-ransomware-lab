"""Parse bandit security scan output."""

import json
import subprocess
import sys


def parse(path: str = "src/") -> dict:
    """Run bandit and return structured results."""
    cmd = [sys.executable, "-m", "bandit", "-r", path, "-f", "json", "-q", "-c", ".bandit"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Failed to parse bandit output", "raw": result.stdout[:500]}
    issues = data.get("results", [])
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_confidence = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for issue in issues:
        sev = issue.get("issue_severity", "LOW")
        conf = issue.get("issue_confidence", "LOW")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_confidence[conf] = by_confidence.get(conf, 0) + 1
    return {
        "total_issues": len(issues),
        "by_severity": by_severity,
        "by_confidence": by_confidence,
        "issues": [
            {
                "id": i.get("test_id", "?"),
                "severity": i.get("issue_severity", "?"),
                "confidence": i.get("issue_confidence", "?"),
                "description": i.get("issue_text", "")[:200],
                "file": i.get("filename", "?"),
                "line": i.get("line_number", 0),
            }
            for i in issues[:50]
        ],
        "metrics": data.get("metrics", {}),
    }
