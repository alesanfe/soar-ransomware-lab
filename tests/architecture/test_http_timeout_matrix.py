"""Architectural gate (R4): every outbound HTTP call carries a timeout.

AST scan over ``src/soar_lab`` — any ``requests.``/``*.Session`` call to
get/post/put/delete/patch/head/request without an explicit ``timeout``
keyword is an unbounded wait that can hang a request handler or a worker
forever. The matrix is uniform today; this test keeps it that way.
"""

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "soar_lab"
HTTP_FUNCS = {"get", "post", "put", "delete", "patch", "head", "request"}


def _receiver_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _receiver_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _calls_without_timeout(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in HTTP_FUNCS:
            continue
        receiver = _receiver_name(node.func.value) or ""
        # Match HTTP receivers only: the last attribute segment must be a
        # session object — excludes dicts (`self._sessions.get`) and
        # header dicts (`client._session.headers.get`).
        last_segment = receiver.rsplit(".", 1)[-1]
        if not (receiver == "requests" or last_segment in ("session", "_session")):
            continue
        if not any(k.arg == "timeout" for k in node.keywords):
            bad.append(f"{path.name}:{node.lineno} {receiver}.{node.func.attr}")
    return bad


def test_every_http_call_has_timeout():
    offenders = []
    for py in SRC.rglob("*.py"):
        offenders.extend(_calls_without_timeout(py))
    assert not offenders, "HTTP calls without explicit timeout:\n" + "\n".join(offenders)
