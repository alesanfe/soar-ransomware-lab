#!/usr/bin/env python3
"""Render Docker config files from templates with env var substitution.

Reads templates from ``infra/docker/config/templates/*.template`` and writes
the rendered files to ``runtime/config/`` so that Docker Compose can mount
them as regular volumes.

The script supports two forms of env-var interpolation:

* ``${VAR}``           — required; warns if not set (leaves placeholder as-is
                        so the service fails loudly with a clear error).
* ``${VAR:-default}``  — optional; uses *default* when the var is not set.

Usage::

    python scripts/setup/render_configs.py [--env-file .env.full]

Intended to be called by ``make up`` before ``docker compose up``.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover
    dotenv_values = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "infra" / "docker" / "config" / "templates"
OUTPUT_DIR = REPO_ROOT / "runtime" / "config"

# ${VAR} or ${VAR:-default}
_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-(.*?))?\}")


def _load_env(env_file: Path | None) -> dict[str, str]:
    """Load env vars from file and os.environ. File takes precedence."""
    env: dict[str, str] = {}
    # Start with os.environ
    for k, v in os.environ.items():
        env[k] = v
    # Override with .env file (if provided)
    if env_file and env_file.exists():
        if dotenv_values:
            file_env = dotenv_values(env_file)
            env.update(file_env)
        else:
            # Manual parse fallback
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def _substitute(text: str, env: dict[str, str], template_name: str) -> str:
    """Replace ${VAR} and ${VAR:-default} placeholders."""

    def replacer(m: re.Match) -> str:
        var = m.group(1)
        default = m.group(2)
        val = env.get(var)
        if val is not None and val != "":
            return val
        if default is not None:
            return default
        logger.warning(
            "%s: ${{%s}} is not set and has no default — "
            "the rendered config will contain the literal placeholder",
            template_name,
            var,
        )
        return m.group(0)

    return _VAR_RE.sub(replacer, text)


def render_all(env: dict[str, str], output_dir: Path) -> list[Path]:
    """Render all templates. Returns list of rendered file paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for template in sorted(TEMPLATES_DIR.glob("*.template")):
        # Strip ".template" suffix for output name
        out_name = template.name.removesuffix(".template")
        out_path = output_dir / out_name
        text = template.read_text(encoding="utf-8")
        rendered_text = _substitute(text, env, template.name)
        out_path.write_text(rendered_text, encoding="utf-8")
        rendered.append(out_path)
        logger.info("Rendered %s -> %s", template.name, out_path.relative_to(REPO_ROOT))
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=REPO_ROOT / ".env.full",
        help="Path to .env file (default: .env.full)",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=TEMPLATES_DIR,
        help="Directory containing *.template files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory to write rendered configs",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.templates_dir.exists():
        logger.error("Templates directory not found: %s", args.templates_dir)
        return 1

    env = _load_env(args.env_file)

    rendered = render_all(env, args.output_dir)
    if not rendered:
        logger.warning("No templates found in %s", args.templates_dir)
        return 1

    print(f"Rendered {len(rendered)} config files to {args.output_dir.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
