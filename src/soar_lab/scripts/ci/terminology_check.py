#!/usr/bin/env python3
"""Terminology checker for documentation.

Scans Markdown files for inconsistent or legacy terms and reports occurrences.
This is used in CI to keep docs terminology aligned with the canonical project
terms. It does not enforce Spanish spelling/grammar; it only flags
inconsistencies and legacy technical terms.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_TERMS: dict[str, re.Pattern] = {
    # Prefer these canonical forms. Values are case-insensitive regexes.
    "src/soar_lab/infrastructure/setup": re.compile(
        r"\bsrc/soar_lab/infrastructure/setup\b", re.IGNORECASE
    ),
    "src/soar_lab/infrastructure/scripts": re.compile(
        r"\bsrc/soar_lab/infrastructure/scripts\b", re.IGNORECASE
    ),
    "src/scripts": re.compile(r"\bsrc/scripts\b", re.IGNORECASE),
    "src/api": re.compile(r"\bsrc/api\b", re.IGNORECASE),
    "README 1001": re.compile(r"1001\s+passed"),
    "total_time_manual": re.compile(r"\btotal_time_manual\b"),
    "infrastructure/setup": re.compile(r"\binfrastructure/setup\b", re.IGNORECASE),
    "infrastructure/scripts": re.compile(r"\binfrastructure/scripts\b", re.IGNORECASE),
}

# Terms that are valid in some contexts but should be reviewed for consistency.
REVIEW_TERMS: dict[str, re.Pattern] = {}

# Exceptions: files or directories that are intentionally historical.
EXCLUDED_DIRS = {"legacy", "node_modules", ".git", "build", "dist", "__pycache__"}
EXCLUDED_FILES = {"CHANGELOG_THESIS_UPDATE.md", "audit"}


def collect_markdown_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            for md in path.rglob("*.md"):
                if any(part in EXCLUDED_DIRS for part in md.parts):
                    continue
                if md.name in EXCLUDED_FILES:
                    continue
                yield md
        elif path.is_file() and path.suffix == ".md":
            if all(part not in EXCLUDED_DIRS for part in path.parts) and path.name not in EXCLUDED_FILES:
                yield path


def check_file(md: Path, terms: dict[str, re.Pattern], review_terms: dict[str, re.Pattern] | None = None) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    review_notes: list[str] = []
    try:
        text = md.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{md}: cannot decode ({exc})"], []

    def line_no(pos: int) -> int:
        return text[:pos].count("\n") + 1

    def line_text(pos: int) -> str:
        start = text.rfind("\n", 0, pos) + 1
        end = text.find("\n", pos)
        if end == -1:
            end = len(text)
        return text[start:end]

    skip_words = {"legacy", "histórico", "históricos", "obsoleto"}

    def context_has_skip_word(pos: int) -> bool:
        start = max(0, text.rfind("\n", 0, pos))
        # include one line before
        start = max(0, text.rfind("\n", 0, start))
        end = text.find("\n", pos)
        if end == -1:
            end = len(text)
        # include one line after
        next_end = text.find("\n", end + 1)
        if next_end == -1:
            next_end = len(text)
        ctx = text[start:next_end].lower()
        return any(word in ctx for word in skip_words)

    for term_name, pattern in terms.items():
        for match in pattern.finditer(text):
            if context_has_skip_word(match.start()):
                continue
            issues.append(f"{md}:{line_no(match.start())}: legacy/inconsistent term {term_name!r}")

    if review_terms:
        for term_name, pattern in review_terms.items():
            for match in pattern.finditer(text):
                review_notes.append(f"{md}:{line_no(match.start())}: review term {term_name!r}")

    return issues, review_notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check docs for legacy terminology")
    parser.add_argument("paths", nargs="+", type=Path, help="Markdown files or directories to scan")
    parser.add_argument(
        "--no-legacy-dirs",
        action="store_true",
        help="Skip docs/audit/legacy and other historical folders",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat review terms as errors",
    )
    args = parser.parse_args(argv)

    if args.no_legacy_dirs:
        EXCLUDED_DIRS.add("legacy")

    files = list(collect_markdown_files(args.paths))
    all_issues: list[str] = []
    all_reviews: list[str] = []
    for md in files:
        issues, reviews = check_file(md, DEFAULT_TERMS, REVIEW_TERMS)
        all_issues.extend(issues)
        all_reviews.extend(reviews)

    if all_issues:
        print(f"Found {len(all_issues)} terminology issue(s):")
        for issue in all_issues:
            print(issue)

    if all_reviews:
        print(f"Found {len(all_reviews)} term(s) to review (context-dependent):")
        for note in all_reviews:
            print(note)

    if all_issues or (args.strict and all_reviews):
        return 1

    if not all_issues and not all_reviews:
        print(f"No terminology issues found in {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
