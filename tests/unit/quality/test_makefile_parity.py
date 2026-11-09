"""INFRA-01: Makefile.win / Makefile.linux target parity gate."""

import importlib.util
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "Makefile.win").is_file())
SCRIPT = ROOT / "scripts" / "ci" / "check_makefile_parity.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_makefile_target_parity():
    mod = _load("check_makefile_parity", SCRIPT)
    win = mod.targets(ROOT / "Makefile.win")
    lin = mod.targets(ROOT / "Makefile.linux")
    win_only = sorted(win - lin)
    lin_only = sorted(lin - win)
    assert (
        not win_only and not lin_only
    ), f"Makefile target drift — win-only: {win_only}, linux-only: {lin_only}"
