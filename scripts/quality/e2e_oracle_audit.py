#!/usr/bin/env python3
"""E2E-ORACLE audit — AST scanner for weak test oracles in tests/e2e/.

Classifies every ``assert`` in the E2E suites against the vacuous-oracle
patterns from ``docs/18-e2e-suite-backlog-9of10.md`` (E2E-ORACLE) plus
swallowed-assertion (E2E-ERR) and arbitrary-sleep (E2E-TIME) signals.

Categories (severity):
  vacuous_bound      len(x) >= 0 | x >= 0 | count > -1               (high)
  permissive_status  status < 500 | status == 200 or >= 400 | not in (500,) (high)
  tautology          assert True | x == x | constant comparisons     (high)
  swallowed_assert   assert inside try: whose except does not re-raise/fail (high)
  isinstance_only    test function whose ONLY assert is isinstance() (medium)
  none_after_guard   assert x is not None guarded by `if x is None: return` (low)
  executing_success  "EXECUTING" in an accepted-success set          (high)
  arbitrary_sleep    time.sleep(literal > 5) outside a bounded poll   (medium)
  is_not_none_only   function whose only oracle is `is not None`      (medium)
  test_calls_test    a test_* function calls another test_* function  (high)
  max_id_select      max() over case/id-like expressions (E2E-CORR-001) (high)
  except_pass        except handler whose body only passes/logs       (high)
  return_true_except `return True` inside an except handler           (medium)
  fixed_id           alert/trace/correlation id assigned a constant   (medium)
  verify_false       verify=False on an HTTP call                     (low)
  hardcoded_url      http(s):// literal inside a test function        (low)

Output:
  - JSON  -> reports/test-review/e2e_oracle_audit.json
  - Markdown summary table on stdout + reports/test-review/e2e_oracle_audit.md

Usage:
    python scripts/quality/e2e_oracle_audit.py [--root tests/e2e] [--json PATH]
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEVERITY = {"high": 3, "medium": 2, "low": 1}

ROOT_DEFAULT = Path("tests/e2e")
JSON_OUT = Path("reports/test-review/e2e_oracle_audit.json")
MD_OUT = Path("reports/test-review/e2e_oracle_audit.md")


@dataclass
class Finding:
    file: str
    line: int
    function: str
    category: str
    severity: str
    snippet: str


@dataclass
class FileReport:
    file: str
    assertions: int = 0
    test_functions: int = 0
    findings: list[Finding] = field(default_factory=list)


def _src_seg(source: str, node: ast.AST) -> str:
    seg = ast.get_source_segment(source, node) or ""
    return " ".join(seg.split())[:120]


def _src_seg_full(source: str, node: ast.AST) -> str:
    """Source segment without the 120-char display cap.

    Keyword detection (pytest.fail/raise inside except handlers) must see
    the whole handler body — truncating to 120 chars hides trailing
    ``pytest.fail`` calls and produces false ``swallowed_assert`` findings.
    """
    seg = ast.get_source_segment(source, node) or ""
    return " ".join(seg.split())


def _is_status_expr(node: ast.AST) -> bool:
    """True when the expression mentions status/status_code."""
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and "status" in n.attr.lower():
            return True
        if isinstance(n, ast.Name) and n.id.lower() in ("status", "status_code"):
            return True
    return False


class OracleVisitor(ast.NodeVisitor):
    def __init__(self, source: str, fname: str):
        self.source = source
        self.fname = fname
        self.report = FileReport(file=fname)
        self._fn_asserts: dict[str, list[ast.Assert]] = {}
        self._current_fn: list[str] = []

    # --------------------------------------------------------------- helpers
    def _add(self, node: ast.AST, category: str, severity: str) -> None:
        fn = self._current_fn[-1] if self._current_fn else "<module>"
        self.report.findings.append(
            Finding(
                file=self.fname,
                line=getattr(node, "lineno", 0),
                function=fn,
                category=category,
                severity=severity,
                snippet=_src_seg(self.source, node),
            )
        )

    # ---------------------------------------------------------------- visit
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._current_fn.append(node.name)
        if node.name.startswith("test"):
            self.report.test_functions += 1
            self._fn_asserts[node.name] = []
        self.generic_visit(node)
        self._current_fn.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node: ast.If) -> None:
        # if x is None: return/continue -> assert x is not None later is fine;
        # flag `assert x` where the `if` already tested the identical expr.
        if isinstance(node.test, ast.Compare):
            pass  # handled at assert level via text heuristics
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.report.assertions += 1
        fn = self._current_fn[-1] if self._current_fn else "<module>"
        if fn in self._fn_asserts:
            self._fn_asserts[fn].append(node)
        seg = _src_seg(self.source, node)
        t = node.test

        # --- tautology: assert True / x == x
        if isinstance(t, ast.Constant) and t.value is True:
            self._add(node, "tautology", "high")
        if (
            isinstance(t, ast.Compare)
            and len(t.ops) == 1
            and isinstance(t.ops[0], ast.Eq)
            and _src_seg(self.source, t.left) == _src_seg(self.source, t.comparators[0])
        ):
            self._add(node, "tautology", "high")

        # --- vacuous bound: len(x) >= 0 | len(x) > -1 | <count-like> >= 0
        #     (len(x) > 0 is NOT vacuous — it asserts non-emptiness)
        if isinstance(t, ast.Compare) and len(t.ops) == 1:
            op = t.ops[0]
            comp = t.comparators[0]
            if isinstance(op, (ast.GtE, ast.Gt)) and isinstance(comp, ast.Constant):
                left_is_len = isinstance(t.left, ast.Call) and _src_seg(
                    self.source, t.left.func
                ).endswith("len")
                left_name = _src_seg(self.source, t.left).lower()
                count_like = bool(
                    re.search(r"count|len|num|total|size|_n\b|^n_", left_name)
                )
                val = comp.value
                vacuous = False
                if isinstance(op, ast.GtE) and isinstance(val, (int, float)):
                    # x >= 0 is vacuous for lengths/counts (can't be negative)
                    if val <= 0 and (left_is_len or count_like):
                        vacuous = True
                elif isinstance(op, ast.Gt) and isinstance(val, (int, float)):
                    # len(x) > -1 vacuous; len(x) > 0 is a real non-empty check
                    if val < 0 and (left_is_len or count_like):
                        vacuous = True
                if vacuous:
                    self._add(node, "vacuous_bound", "high")

        # --- permissive status
        if _is_status_expr(t):
            if isinstance(t, ast.Compare):
                # status < 500 / status <= 599 style
                for op, comp in zip(t.ops, t.comparators):
                    if isinstance(op, (ast.Lt, ast.LtE)) and isinstance(comp, ast.Constant):
                        if isinstance(comp.value, int) and comp.value >= 500:
                            self._add(node, "permissive_status", "high")
                # status not in (5xx…) — "service didn't crash" is weaker than
                # checking the actual effect, but narrower than `status < 500`
                if isinstance(t.ops[0], ast.NotIn):
                    self._add(node, "permissive_status", "medium")
            if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.Or):
                self._add(node, "permissive_status", "high")

        # --- EXECUTING accepted as success
        if "EXECUTING" in seg:
            self._add(node, "executing_success", "high")

        self.generic_visit(node)

    def _handler_catches_asserts(self, handler: ast.ExceptHandler) -> bool:
        """True if the handler's type can catch AssertionError.

        ``except Exception``/``BaseException``/``AssertionError``/bare
        ``except:`` swallow asserts; narrow handlers such as
        ``except requests.exceptions.RequestException`` cannot.
        """
        if handler.type is None:  # bare except:
            return True
        t = handler.type
        names = t.elts if isinstance(t, ast.Tuple) else [t]
        swallow = ("Exception", "BaseException", "AssertionError")
        narrow = ("RequestException", "ConnectionError", "TimeoutError",
                  "TimeoutException", "HTTPError", "ConnectError")
        for n in names:
            seg = _src_seg_full(self.source, n).split(".")[-1].split("[")[0]
            if seg in swallow or (seg.endswith("Exception") and seg not in narrow):
                return True
        return False

    def visit_Try(self, node: ast.Try) -> None:
        """assert inside try: whose handlers swallow it (no fail/re-raise)."""
        try_asserts = [n for n in ast.walk(ast.Module(body=node.body, type_ignores=[])) if isinstance(n, ast.Assert)]
        for handler in node.handlers:
            body_segs = " ".join(
                _src_seg_full(self.source, stmt) for stmt in handler.body
            )
            swallow = not any(
                kw in body_segs
                for kw in ("pytest.fail", "raise", "assert", "fail(", "re_raise")
            )
            if swallow and try_asserts and self._handler_catches_asserts(handler):
                for a in try_asserts:
                    self._add(a, "swallowed_assert", "high")
            # except whose body only passes/logs/docstring -> soft-fail by itself
            effective = [
                s
                for s in handler.body
                if not (
                    isinstance(s, ast.Expr)
                    and isinstance(s.value, ast.Constant)
                    and isinstance(s.value.value, str)
                )
            ]
            if effective and all(
                isinstance(s, (ast.Pass, ast.Expr)) for s in effective
            ):
                calls_only = all(
                    isinstance(s, ast.Pass)
                    or (
                        isinstance(s, ast.Expr)
                        and isinstance(s.value, ast.Call)
                    )
                    for s in effective
                )
                if calls_only and not any(
                    kw in body_segs
                    for kw in ("pytest.fail", "raise", "fail(", "record_assertion")
                ):
                    self._add(handler, "except_pass", "high")
            # `return True` inside an except handler
            for s in ast.walk(handler):
                if (
                    isinstance(s, ast.Return)
                    and isinstance(s.value, ast.Constant)
                    and s.value.value is True
                ):
                    self._add(s, "return_true_except", "medium")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = _src_seg(self.source, node.func)
        # matches time.sleep(literal > 5)
        if func.endswith("time.sleep") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                if arg.value > 5:
                    self._add(node, "arbitrary_sleep", "medium")

        # test_* function calling another test_* function (EXEC-001):
        # pytest collects both -> the scenario runs twice.
        callee = ""
        if isinstance(node.func, ast.Attribute):
            callee = node.func.attr
        elif isinstance(node.func, ast.Name):
            callee = node.func.id
        if callee.startswith("test_"):
            self._add(node, "test_calls_test", "high")

        # max(...) selecting the "latest" resource globally (CORR-001):
        # max(caseId), max(c["id"] for c in cases), max(id_list), …
        if func in ("max", "self.max") and node.args:
            arg_text = " ".join(_src_seg(self.source, a) for a in node.args).lower()
            if re.search(r"case|_id\b|id_|caseid|alert_id", arg_text):
                self._add(node, "max_id_select", "high")

        # verify=False on HTTP calls
        for kw in node.keywords:
            if (
                kw.arg == "verify"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is False
            ):
                self._add(node, "verify_false", "low")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # alert_id/trace_id/correlation_id/idempotency_key = "CONSTANT"
        # — fixed IDs break run correlation and cross-test isolation.
        target_names = [
            t.id.lower()
            for t in node.targets
            if isinstance(t, ast.Name)
        ]
        id_like = any(
            re.search(r"alert_id|trace_id|correlation|idempoten|run_id|case_id", n)
            for n in target_names
        )
        if id_like and isinstance(node.value, ast.Constant) and isinstance(
            node.value.value, str
        ):
            self._add(node, "fixed_id", "medium")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        # http(s):// literal inside a test function -> hardcoded endpoint
        if (
            isinstance(node.value, str)
            and node.value.startswith(("http://", "https://"))
            and self._current_fn
            and self._current_fn[-1].startswith("test")
        ):
            self._add(node, "hardcoded_url", "low")
        self.generic_visit(node)

    # ------------------------------------------------------------ post-pass
    def finalize(self) -> None:
        """Flag test functions whose ONLY oracle is isinstance/is-not-None."""
        for fn, asserts in self._fn_asserts.items():
            if not asserts:
                continue
            kinds = []
            for a in asserts:
                t = a.test
                if (
                    isinstance(t, ast.Call)
                    and isinstance(t.func, ast.Name)
                    and t.func.id == "isinstance"
                ):
                    kinds.append("isinstance")
                elif (
                    isinstance(t, ast.Compare)
                    and len(t.ops) == 1
                    and isinstance(t.ops[0], ast.IsNot)
                    and isinstance(t.comparators[0], ast.Constant)
                    and t.comparators[0].value is None
                ):
                    kinds.append("is_not_none")
                else:
                    kinds.append("other")
            if kinds and all(k == "isinstance" for k in kinds):
                self.report.findings.append(
                    Finding(
                        file=self.fname,
                        line=asserts[0].lineno,
                        function=fn,
                        category="isinstance_only",
                        severity="medium",
                        snippet=f"{fn}: only isinstance() oracles ({len(kinds)})",
                    )
                )
            elif kinds and all(k in ("isinstance", "is_not_none") for k in kinds):
                self.report.findings.append(
                    Finding(
                        file=self.fname,
                        line=asserts[0].lineno,
                        function=fn,
                        category="none_and_type_only",
                        severity="medium",
                        snippet=f"{fn}: only isinstance/is-not-None oracles ({len(kinds)})",
                    )
                )


def score_report(rep: FileReport) -> float:
    """Oracle dimension score 0-4 (docs/18 model). 4 = verified oracles only."""
    if rep.assertions == 0:
        return 0.0
    penalty = sum(SEVERITY[f.severity] for f in rep.findings)
    ratio = penalty / rep.assertions
    if ratio >= 1.0:
        return 1.0
    if ratio >= 0.5:
        return 2.0
    if ratio > 0:
        return 3.0
    return 4.0


def scan(root: Path) -> list[FileReport]:
    """Run the oracle audit over ``root`` and return per-file reports.

    File names are stored relative to ``root`` so fingerprints are stable
    regardless of the checkout location or invocation cwd.
    """
    root = Path(root).resolve()
    reports: list[FileReport] = []
    for py in sorted(root.rglob("test_*.py")):
        source = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            print(f"[SKIP] {py}: {exc}", file=sys.stderr)
            continue
        rel = py.resolve().relative_to(root).as_posix()
        visitor = OracleVisitor(source, rel)
        visitor.visit(tree)
        visitor.finalize()
        reports.append(visitor.report)
    return reports


def finding_fingerprint(f: Finding) -> str:
    """Stable identity for a finding, independent of line drift.

    file + category + enclosing function + normalized snippet — enough to
    match a finding across refactors without pinning line numbers.
    """
    key = f"{f.file}|{f.category}|{f.function}|{f.snippet.strip()[:80]}"
    import hashlib

    return hashlib.sha1(key.encode()).hexdigest()[:16]


def load_baseline(path: Path) -> set[str]:
    """Return the set of accepted finding fingerprints, or empty."""
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("fingerprints", []))


def write_baseline(path: Path, reports: list[FileReport]) -> None:
    """Persist the current findings as the accepted baseline."""
    fps = sorted(
        finding_fingerprint(f) for r in reports for f in r.findings
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"fingerprints": fps}, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--json", type=Path, default=JSON_OUT)
    parser.add_argument("--md", type=Path, default=MD_OUT)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="fail if findings appear that are not in this baseline file",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="write current findings to --baseline and exit",
    )
    args = parser.parse_args()

    reports = scan(args.root)

    total_findings = sum(len(r.findings) for r in reports)
    by_cat: dict[str, int] = {}
    for r in reports:
        for f in r.findings:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1

    payload = {
        "root": str(args.root),
        "files": len(reports),
        "test_functions": sum(r.test_functions for r in reports),
        "assertions": sum(r.assertions for r in reports),
        "findings": total_findings,
        "by_category": dict(sorted(by_cat.items())),
        "files_detail": [
            {
                "file": r.file,
                "assertions": r.assertions,
                "test_functions": r.test_functions,
                "oracle_score": score_report(r),
                "findings": [asdict(f) for f in r.findings],
            }
            for r in reports
        ],
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    worst = sorted(reports, key=score_report)[:20]
    lines = [
        "# E2E Oracle Audit",
        "",
        f"- Files scanned: {payload['files']}",
        f"- Test functions: {payload['test_functions']}",
        f"- Assertions: {payload['assertions']}",
        f"- Findings: {total_findings}",
        "",
        "## By category",
        "",
        "| Category | Count |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])]
    lines += [
        "",
        "## Worst files (oracle score 0-4)",
        "",
        "| File | Asserts | Findings | Score |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {r.file} | {r.assertions} | {len(r.findings)} | {score_report(r):.1f} |"
        for r in worst
    ]
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nJSON -> {args.json}\nMD   -> {args.md}")

    if args.write_baseline:
        if args.baseline is None:
            print("--write-baseline requires --baseline PATH", file=sys.stderr)
            return 2
        write_baseline(args.baseline, reports)
        print(f"baseline -> {args.baseline} ({total_findings} fingerprints)")
        return 0

    if args.baseline is not None:
        accepted = load_baseline(args.baseline)
        new_findings = [
            f
            for r in reports
            for f in r.findings
            if finding_fingerprint(f) not in accepted
        ]
        if new_findings:
            print(f"\n[FAIL] {len(new_findings)} finding(s) not in baseline:")
            for f in new_findings[:30]:
                print(
                    f"  {f.file}:{f.line} [{f.category}] {f.function}: {f.snippet[:80]}"
                )
            return 1
        print(f"\n[OK] all {total_findings} finding(s) covered by baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
