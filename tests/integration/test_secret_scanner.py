"""BL-SEC-013: the tracked tree must stay free of committed secrets.

Lives in integration because it shells out to git via the scanner
script — unit tests may not spawn subprocesses per tests/unit/conftest.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repo_has_no_committed_secrets():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "safety" / "scan_secrets.py")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout[-2000:]
