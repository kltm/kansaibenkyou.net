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

import yaml

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "_site"
DATA = REPO / "data"

# Per-collection thresholds for "meaningful content" in chars stripped from
# <article>. Words can be legitimately terse ("body: corn" at ~70 chars);
# grammar points and conversations carry substantial prose and should always
# exceed 100. Taxonomy pages use 100 so we catch the case where a term has
# a glossary description in data but the layout fails to render it — the
# exact failure mode that drove the deletion of 58 taxonomy term pages last
# cycle.
MIN_CONTENT_TAXONOMY = 100
MIN_CONTENT_COLLECTION = 40

# Collection directory names as they appear under _site/ (hyphenated, matching
# the permalinks in _config.yml — NOT the underscored data/ source dirs).
COLLECTION_DIRS = [
    "words",
    "grammar-points",
    "real-conversations",
    "example-conversations",
    "phonology",
]


def check_page(html_path: Path, threshold: int) -> tuple[bool, int]:
    """Return (has_content, content_length).

    Redirect stubs (pages with a `<meta http-equiv="refresh">`) are
    considered non-empty — they are intentional navigation helpers,
    not missing content.
    """
    html = html_path.read_text(errors="replace")

    if re.search(r'<meta\s+http-equiv=["\']refresh["\']', html, re.IGNORECASE):
        return True, -1

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

    return len(text) >= threshold, len(text)


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def main() -> None:
    # Load taxonomy data to distinguish "empty layout" from "empty data".
    # A term is genuinely empty only if it has NO description AND NO
    # reverse-index entries — matching the pedagogical definition: a term
    # with a glossary definition OR a non-empty reverse index is a useful
    # page even when its HTML body is short. This guards the regression
    # in which 58 term pages were deleted after their reverse index was
    # misread as "no content".
    descriptions = load_yaml(DATA / "taxonomy_descriptions.yaml")
    index = load_yaml(DATA / "taxonomy_index.yaml")

    # Check taxonomy term pages.
    #
    # Semantics: a term page is "non-empty" if its underlying YAML data
    # contains EITHER a description OR at least one reverse-index entry.
    # We don't rely on rendered-HTML char count for this category,
    # because a legitimate glossary definition can be 20-30 chars
    # ("Abbreviation for verb.") and that is still a valid page.
    #
    # layout_empty_terms: HTML is almost entirely empty (a layout bug
    #   even for short-description terms — means the description isn't
    #   rendering at all).
    # data_empty_terms: no description AND no index entries — a content
    #   backlog item, not a failure.
    layout_empty_terms = []
    data_empty_terms = []
    LAYOUT_EMPTY_THRESHOLD = 20  # < this many chars means nothing rendered
    term_dir = SITE / "taxonomy" / "term"
    if term_dir.exists():
        for d in sorted(term_dir.iterdir()):
            idx = d / "index.html"
            if not idx.exists():
                continue
            _has_content, length = check_page(idx, MIN_CONTENT_TAXONOMY)
            tid = str(d.name)
            has_desc = bool(descriptions.get(tid))
            idx_entry = index.get(tid) or {}
            has_idx = (any(idx_entry.values())
                       if isinstance(idx_entry, dict) else bool(idx_entry))
            if has_desc or has_idx:
                # Data present. Only flag if the HTML is genuinely not
                # rendering anything — indicates a layout bug.
                if length < LAYOUT_EMPTY_THRESHOLD:
                    layout_empty_terms.append((tid, length, has_desc, has_idx))
                continue
            # No data — backlog.
            data_empty_terms.append((tid, length))

    # Check all collection pages for emptiness.
    empty_others = []
    for collection_dir in COLLECTION_DIRS:
        cdir = SITE / collection_dir
        if not cdir.exists():
            print(f"  warning: collection dir not found: _site/{collection_dir}")
            continue
        for d in sorted(cdir.iterdir()):
            idx = d / "index.html"
            if idx.exists():
                has_content, length = check_page(idx, MIN_CONTENT_COLLECTION)
                if not has_content:
                    empty_others.append((f"/{collection_dir}/{d.name}/", length))

    print(f"Taxonomy terms with empty HTML but data present (layout bug): "
          f"{len(layout_empty_terms)}")
    for tid, length, has_desc, has_idx in layout_empty_terms[:20]:
        flags = []
        if has_desc:
            flags.append("desc")
        if has_idx:
            flags.append("idx")
        print(f"  /taxonomy/term/{tid}/ ({length} chars; has {'+'.join(flags)})")
    if len(layout_empty_terms) > 20:
        print(f"  ... and {len(layout_empty_terms) - 20} more")

    print(f"\nTaxonomy terms with no description AND no reverse-index "
          f"(data missing): {len(data_empty_terms)}")
    for tid, length in data_empty_terms[:20]:
        print(f"  /taxonomy/term/{tid}/ ({length} chars)")
    if len(data_empty_terms) > 20:
        print(f"  ... and {len(data_empty_terms) - 20} more")

    print(f"\nEmpty collection pages: {len(empty_others)}")
    for path, length in empty_others[:20]:
        print(f"  {path} ({length} chars)")
    if len(empty_others) > 20:
        print(f"  ... and {len(empty_others) - 20} more")

    # For --strict: fail on layout bugs and on empty collection pages.
    # Do NOT fail on data_empty_terms alone — that's a content backlog,
    # not a regression. Report, but don't gate CI on it.
    failing = len(layout_empty_terms) + len(empty_others)
    print(f"\nFailures (layout-bug terms + empty collection pages): {failing}")
    print(f"Data-missing terms (backlog, not a failure): {len(data_empty_terms)}")
    if failing > 0 and "--strict" in sys.argv:
        sys.exit(1)


if __name__ == "__main__":
    main()
