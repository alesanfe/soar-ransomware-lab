#!/usr/bin/env python3
"""CI gate (R4): every outbound HTTP call must set an explicit timeout.

A bare ``requests.get/post/...`` or ``session.request(...)`` without
``timeout=`` hangs forever on a dead peer — the bug class behind the
"uniform timeout matrix" item. ``BaseHTTPClient`` already enforces
timeouts centrally; this gate covers the raw-call surface so new code
cannot regress it.

AST-based: checks the *call's* keyword arguments (not the text line),
so multi-line invocations are evaluated correctly.

Exits 1 listing offending call sites.
"""

import ast
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "request"}


def _is_http_call(node: ast.Call) -> bool:
    """True for requests-style calls on surfaces without a baked timeout.

    Covered: ``requests.<verb>(...)`` and ``<x containing 'session'>
    .<verb>(...)``/``.request(...)``. Excluded: receivers named
    ``*client*`` — those are transport facades (``http_client``,
    ``_client`` ES wrapper, redis client) that own their timeout
    policy, plus dict-like ``.get`` on non-HTTP objects.
    """
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in HTTP_METHODS:
        return False
    recv = func.value
    if isinstance(recv, ast.Name) and recv.id == "requests":
        return True
    name = ""
    while isinstance(recv, ast.Attribute):
        name = recv.attr
        recv = recv.value
    if isinstance(recv, ast.Name):
        name = recv.id if not name else f"{recv.id}.{name}"
    if "client" in name.lower():
        return False
    # 'session' as a singular token — 'sessions' is the pooled dict in
    # http_client, not a requests.Session.
    return re.search(r"session(?!s\b)", name.lower()) is not None


def _has_timeout(node: ast.Call) -> bool:
    for kw in node.keywords:
        if kw.arg == "timeout":
            return True
        # **kwargs passthrough may carry a timeout — allow it.
        if kw.arg is None:
            return True
    return False


def main() -> int:
    offenders: list[str] = []
    for py in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_http_call(node) and not _has_timeout(node):
                offenders.append(f"{py.relative_to(SRC)}:{node.lineno}")

    if offenders:
        print("HTTP calls without explicit timeout (R4):")
        for o in offenders:
            print(f"  {o}")
        return 1
    print("R4 gate OK — every raw HTTP call sets a timeout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
