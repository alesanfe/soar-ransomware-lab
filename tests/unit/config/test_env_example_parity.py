"""Parity test: every env var read by Settings must exist in .env.example.

An env var consumed by ``os.getenv`` in ``settings.py`` but absent from
``.env.example`` is an undocumented configuration surface — operators
cannot discover it without reading source. This test fails the moment
a new var is introduced without documentation.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_SRC = REPO_ROOT / "src" / "soar_lab" / "config" / "settings.py"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

GETENV_RE = re.compile(r"""os\.getenv\(\s*['"]([A-Z_][A-Z0-9_]*)""")


def _vars_used_in_settings() -> set[str]:
    return set(GETENV_RE.findall(SETTINGS_SRC.read_text(encoding="utf-8")))


def _vars_documented_in_example() -> set[str]:
    documented = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            documented.add(line.split("=", 1)[0].strip())
    return documented


class TestEnvExampleParity:
    def test_every_used_var_is_documented(self):
        missing = _vars_used_in_settings() - _vars_documented_in_example()
        assert not missing, (
            f"env vars used in settings.py but missing from .env.example: " f"{sorted(missing)}"
        )
