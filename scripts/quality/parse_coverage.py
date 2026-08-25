"""Parse coverage.py XML output.

Detects when coverage was not measured (XML exists but has 0 lines) and
returns a clear error message instead of misleading 0%. Falls back to
counting <line> elements when lines-valid attr is missing.
"""

import xml.etree.ElementTree as ET
from pathlib import Path


def parse(xml_path: str = "reports/coverage/coverage.xml") -> dict:
    """Parse coverage XML and return structured results.

    Returns a dict with an 'error' key if coverage was not measured.
    """
    p = Path(xml_path)
    if not p.exists():
        return {
            "error": f"Coverage file not found: {xml_path}",
            "hint": "Run pytest with --cov first",
        }
    tree = ET.parse(p)
    root = tree.getroot()

    # Check if coverage was actually measured
    lines_valid_attr = root.get("lines-valid") or root.get("linesValid")
    total_lines_valid = int(lines_valid_attr) if lines_valid_attr else 0
    lines_covered_attr = root.get("lines-covered") or root.get("linesCovered")
    total_lines_covered = int(lines_covered_attr) if lines_covered_attr else 0

    if total_lines_valid == 0:
        # Check if any class has <line> elements
        has_lines = any(len(list(cls.iter("line"))) > 0 for cls in root.iter("class"))
        if not has_lines:
            return {
                "error": "Coverage XML exists but contains no measured lines",
                "hint": "Run pytest with --cov=src/soar_lab to generate coverage",
            }

    global_line_rate = float(root.get("line-rate", 0)) * 100
    global_branch_rate = float(root.get("branch-rate", 0)) * 100

    files = []
    for cls in root.iter("class"):
        filepath = cls.get("filename", "?")
        line_rate = float(cls.get("line-rate", 0)) * 100
        branch_rate = float(cls.get("branch-rate", 0)) * 100
        # coverage.py doesn't always set branches-valid at class level;
        # detect branches by looking for <line branch="true"> elements
        has_branches = any(
            ln.get("branch") == "true" for ln in cls.iter("line")
        )

        # Count lines manually if lines-valid is missing
        line_elements = list(cls.iter("line"))
        lines_valid = int(cls.get("lines-valid", 0) or 0)
        lines_covered = int(cls.get("lines-covered", 0) or 0)
        if lines_valid == 0 and line_elements:
            lines_valid = len(line_elements)
            lines_covered = sum(1 for ln in line_elements if int(ln.get("hits", 0)) > 0)

        if lines_valid > 0:
            files.append(
                {
                    "filepath": filepath,
                    "line_coverage": round(line_rate, 2),
                    "branch_coverage": round(branch_rate, 2) if has_branches else None,
                    "lines_valid": lines_valid,
                    "lines_covered": lines_covered,
                }
            )

    files.sort(key=lambda x: x["line_coverage"])

    # Aggregate stats (use root attrs if available, else sum from files)
    if total_lines_valid == 0:
        total_lines_valid = sum(f["lines_valid"] for f in files)
        total_lines_covered = sum(f["lines_covered"] for f in files)

    files_below = [f for f in files if f["line_coverage"] < 75]

    return {
        "global_line_coverage": round(global_line_rate, 2),
        "global_branch_coverage": round(global_branch_rate, 2),
        "total_files": len(files),
        "total_lines": total_lines_valid,
        "total_lines_covered": total_lines_covered,
        "files_below_threshold": files_below[:20],
        "files_below_count": len(files_below),
        "worst_files": files[:10],
        "best_files": files[-10:],
    }
