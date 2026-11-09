"""One-off: elevate trivially-safe lazy imports to module top-level.

Handles `import X` / `import X as Y` / `from M import N` lines nested inside
functions where the name is used bare. For `import X as _alias` it rewrites
`_alias.` usages back to `X.` after ensuring `import X` exists at top.
Skips multi-line import statements (continued on following lines).
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path("src/soar_lab")


def top_level_import_end(src: str) -> int:
    """Line index (0-based) after the last top-level import block."""
    lines = src.splitlines()
    last = -1
    in_block = False
    for i, line in enumerate(lines):
        if in_block:
            if line.strip().endswith(")"):
                in_block = False
                last = i
            continue
        if re.match(r"^(from\s+\S+\s+import\s+|import\s+\S)", line):
            last = i
            if line.rstrip().endswith("("):
                in_block = True
    return last


def process(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)

    # collect nested import nodes
    removals: set[int] = set()
    additions: list[str] = []
    rewrites: list[tuple[str, str]] = []  # (_alias -> base)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Import):
                # single-name only `import a` or `import a as b`
                if len(sub.names) != 1:
                    continue
                name, alias = sub.names[0].name, sub.names[0].asname
                stmt = lines[sub.lineno - 1].strip()
                if stmt.startswith("import ") and "#" not in stmt:
                    removals.add(sub.lineno - 1)
                    if alias:
                        rewrites.append((alias, name))
                        additions.append(f"import {name}")
                    else:
                        additions.append(f"import {name}")
            elif isinstance(sub, ast.ImportFrom):
                stmt = lines[sub.lineno - 1].strip()
                # only single-line statements
                if "(" in stmt or not stmt.startswith("from "):
                    continue
                removals.add(sub.lineno - 1)
                additions.append(stmt)

    if not removals:
        return []

    body = [l for i, l in enumerate(lines) if i not in removals]
    new_src = "\n".join(body) + ("\n" if src.endswith("\n") else "")

    # apply alias rewrites: _req. -> requests. ; (_req) -> (requests)
    for alias, base in rewrites:
        new_src = re.sub(rf"\b{re.escape(alias)}\b", base, new_src)

    # insert missing top-level imports after last import block
    lines = new_src.splitlines()
    insert_at = top_level_import_end(new_src) + 1
    existing = {l.strip() for l in lines}
    to_add = [a for a in additions if a not in existing]
    if to_add:
        lines[insert_at:insert_at] = to_add
    new_src = "\n".join(lines)
    if src.endswith("\n") and not new_src.endswith("\n"):
        new_src += "\n"

    ast.parse(new_src)  # safety: must still parse
    path.write_text(new_src, encoding="utf-8")
    return sorted(set(additions))


files = sys.argv[1:]
for f in files:
    p = Path(f)
    added = process(p)
    print(p, "->", added if added else "no-op")
