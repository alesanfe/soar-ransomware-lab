#!/usr/bin/env python3
"""Regression tests for scripts/reports/test_summary.py.

BUG-038: ``_run_suite`` built a single ``shell=True`` command string where
the pytest ``-m`` marker expression was wrapped in *single* quotes. On
Windows, ``cmd.exe`` does not group single-quoted text, so the expression
split into positional args — pytest then read ``requires_external`` as a
file path, exited rc=4 and collected 0 tests, which the summary reported
as PASS (0 failures). Fix: argv list, no shell, marker as one token.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = ROOT / "scripts" / "reports" / "test_summary.py"
if not _SCRIPT.exists():
    # container image baked before the script existed (tests/ is mounted,
    # scripts/ is baked) — skip rather than break collection
    pytest.skip("test_summary.py not present in this environment", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("test_summary", _SCRIPT)
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)


def _captured_cmds(monkeypatch):
    calls = []

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *a, **kw):
        calls.append((cmd, kw))
        return _Proc()

    monkeypatch.setattr(ts.subprocess, "run", fake_run)
    monkeypatch.setattr(
        ts,
        "_parse_junit",
        lambda p: {"tests": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
    )
    return calls


def test_run_suite_passes_marker_as_single_argv_token(tmp_path, monkeypatch):
    calls = _captured_cmds(monkeypatch)
    ts._run_suite("integration", tmp_path)

    cmd, kwargs = calls[0]
    assert kwargs.get("shell") is not True, "shell=True tokenizes wrong on Windows cmd.exe"
    assert isinstance(cmd, list), "must use argv list, not a shell string"
    m = cmd.index("-m", cmd.index("pytest"))  # pytest's -m, not python3's
    assert cmd[m + 1] == "not requires_external and not requires_docker"
    assert not any("'" in arg for arg in cmd), "stray quote chars reach the argv literally"


def test_run_suite_docker_cp_also_argv(tmp_path, monkeypatch):
    calls = _captured_cmds(monkeypatch)
    ts._run_suite("unit", tmp_path)

    _, kwargs = calls[1]
    assert kwargs.get("shell") is not True
    assert isinstance(calls[1][0], list)
