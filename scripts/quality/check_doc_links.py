#!/usr/bin/env python3
"""DOCS-005/006: check (and optionally fix) same-page heading anchors and
intra-docs markdown links in docs/*.md.

- Computes GitHub-slugger anchors for every ATX heading.
- `#anchor` links not matching any heading in the same file are reported;
  with --fix they are rewritten to the closest matching anchor (prefix
  match on the stripped number, else fuzzy ratio >= 0.6).
- `](./file.md)` / `](file.md)` links must resolve inside docs/.

Usage: check_doc_links.py [--fix] [--dir docs]
Exit 0 when no broken same-page anchor/link remains (after fix).
"""

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

HEADING = re.compile(r"^#{1,6}\s+(.*)$")
ANCHOR_LINK = re.compile(r"\]\(#([^)]+)\)")
MD_LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)#\s]+)(#[^)]*)?\)")
# github-slugger: drop punctuation (anything not word/space/hyphen),
# lowercase, spaces -> dashes.
_PUNCT = re.compile(r"[^\w\- ]", re.UNICODE)
# Docusaurus explicit heading ids: `### Title {#custom-id}` — the
# explicit id REPLACES the auto slug, so it must register as an anchor
# (and be stripped before slugging the visible text).
_EXPLICIT_ID = re.compile(r"\{#([^}\s]+)\}")


def slug(text: str) -> str:
    # github-slugger semantics: lowercase, drop punctuation, keep unicode
    # letters (accents are preserved — `#4-validación` is correct).
    text = _PUNCT.sub("", text).strip().lower()
    return text.replace(" ", "-")


def headings(path: Path) -> set[str]:
    out = set()
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADING.match(line)
        if m:
            text = m.group(1)
            for explicit in _EXPLICIT_ID.findall(text):
                out.add(explicit)
            out.add(slug(_EXPLICIT_ID.sub("", text)))
    return out


def best_match(broken: str, anchors: set[str]) -> str | None:
    # numeric prefix match: "#31-nist..." -> "31"
    m = re.match(r"^(\d+)-", broken)
    if m:
        cands = [a for a in anchors if a.startswith(m.group(1) + "-")]
        if len(cands) == 1:
            return cands[0]
        if cands:
            return max(cands, key=lambda a: SequenceMatcher(None, broken, a).ratio())
    cand = max(anchors, key=lambda a: SequenceMatcher(None, broken, a).ratio(), default=None)
    if cand and SequenceMatcher(None, broken, cand).ratio() >= 0.6:
        return cand
    return None


def main() -> int:
    fix = "--fix" in sys.argv
    d = Path(sys.argv[sys.argv.index("--dir") + 1]) if "--dir" in sys.argv else Path("docs")
    files = sorted(d.glob("*.md"))
    broken_total = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        anchors = headings(f)

        def rep(m: re.Match) -> str:
            nonlocal broken_total
            a = m.group(1)
            if a in anchors:
                return m.group(0)
            target = best_match(a, anchors)
            if target:
                broken_total += 1
                print(f"{f.name}: #{a} -> #{target}")
                return f"](#{target})"
            broken_total += 1
            print(f"{f.name}: #{a} -> UNRESOLVED")
            return m.group(0)

        new = ANCHOR_LINK.sub(rep, text)
        if fix and new != text:
            f.write_text(new, encoding="utf-8", newline="")
        # intra-docs file links (same dir): keep report-only
        for m in MD_LINK.finditer(text):
            target = m.group(1)
            if target.startswith(("../", "/")):
                continue
            if not (f.parent / target).exists():
                broken_total += 1
                print(f"{f.name}: link {target} -> FILE MISSING")
    print(f"\n{'fixed/reported' if fix else 'broken'}: {broken_total}")
    return 0 if fix or broken_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
