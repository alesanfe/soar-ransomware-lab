"""Adapter that loads embedded Python scripts as text for Shuffle.

The repository keeps these scripts as real ``.py`` files (so they can be
formatted, linted and tested), but Shuffle needs them as strings inside
the workflow JSON.  This module bridges that gap.
"""

from __future__ import annotations

from pathlib import Path

# Directory containing the embedded scripts
_SCRIPTS_DIR = Path(__file__).parent / "scripts"

# Cache of loaded scripts
_cache: dict[str, str] = {}


def load_script(name: str) -> str:
    """Load a script by name (without ``.py`` extension).

    Raises ``FileNotFoundError`` if the script does not exist.
    """
    if name in _cache:
        return _cache[name]

    path = _SCRIPTS_DIR / f"{name}.py"
    if not path.exists():
        raise FileNotFoundError(
            f"Embedded script not found: {path}\n"
            f"Available scripts: {sorted(p.stem for p in _SCRIPTS_DIR.glob('*.py'))}"
        )

    content = path.read_text(encoding="utf-8")
    # Normalize line endings to \n (Shuffle expects \n in the code string)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    _cache[name] = content
    return content


def load_scripts(names: list[str]) -> dict[str, str]:
    """Load multiple scripts at once.

    Returns ``{name: code_string}``.
    """
    return {name: load_script(name) for name in names}
