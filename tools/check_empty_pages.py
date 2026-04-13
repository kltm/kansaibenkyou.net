#!/usr/bin/env python3
"""Check for pages that exist but have no meaningful content.

Finds taxonomy term pages, word pages, grammar pages, etc. that
render as empty shells — technically a 200 response but no useful
content for the user. These represent broken cross-references: a
link exists to the page, but the page shows nothing.

Usage:

    python3 tools/check_empty_pages.py   # after jekyll build
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "_site"

MIN_CONTENT_LENGTH = 100  # chars of actual text content in <article> or main


def check_page(html_path: Path) -> tuple[bool, int]:
    """Return (has_content, content_length)."""
    html = html_path.read_text(errors="replace")

    # Extract main content area
    m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    if not m:
        m = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
    if not m:
        return False, 0

    content = m.group(1)
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', content)
    text = re.sub(r'\s+', ' ', text).strip()

    return len(text) >= MIN_CONTENT_LENGTH, len(text)


def main() -> None:
    # Check taxonomy term pages
    empty_terms = []
    term_dir = SITE / "taxonomy" / "term"
    if term_dir.exists():
        for d in sorted(term_dir.iterdir()):
            idx = d / "index.html"
            if idx.exists():
                has_content, length = check_page(idx)
                if not has_content:
                    empty_terms.append((d.name, length))

    # Check all collection pages for emptiness
    empty_others = []
    for collection_dir in ["words", "grammar_points", "real_conversations",
                           "example-conversations", "phonology"]:
        cdir = SITE / collection_dir
        if not cdir.exists():
            continue
        for d in sorted(cdir.iterdir()):
            idx = d / "index.html"
            if idx.exists():
                has_content, length = check_page(idx)
                if not has_content:
                    empty_others.append((f"/{collection_dir}/{d.name}/", length))

    print(f"Empty taxonomy term pages: {len(empty_terms)}")
    for name, length in empty_terms[:20]:
        print(f"  /taxonomy/term/{name}/ ({length} chars)")
    if len(empty_terms) > 20:
        print(f"  ... and {len(empty_terms) - 20} more")

    print(f"\nEmpty collection pages: {len(empty_others)}")
    for path, length in empty_others[:20]:
        print(f"  {path} ({length} chars)")

    total = len(empty_terms) + len(empty_others)
    print(f"\nTotal empty pages: {total}")
    if total > 0 and "--strict" in sys.argv:
        sys.exit(1)


if __name__ == "__main__":
    main()
