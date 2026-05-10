#!/usr/bin/env python3
"""Broken link checker for the built Jekyll site.

Crawls _site/ HTML files, finds all href/src attributes, and reports
any that point to non-existent internal paths. Baseurl-aware.

Usage:

    python3 tools/check_links.py           # after jekyll build
    python3 tools/check_links.py --strict  # exit 1 on any broken link
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "_site"
SKIP_PREFIXES = ("http://", "https://", "#", "javascript:", "mailto:", "data:", "//")
SKIP_PATTERNS = ("/pagefind/",)


def main() -> None:
    strict = "--strict" in sys.argv

    base = ""
    config = REPO / "_config.yml"
    if config.exists():
        for line in config.read_text().splitlines():
            m = re.match(r'^baseurl:\s*"?([^"]*)"?', line)
            if m:
                base = m.group(1).strip().rstrip("/")
                break

    existing: set[str] = set()
    for f in SITE.rglob("*"):
        if f.is_file():
            served = base + "/" + str(f.relative_to(SITE))
            existing.add(served)
            if f.name == "index.html":
                parent = base + "/" + str(f.parent.relative_to(SITE))
                existing.add(parent + "/")
                existing.add(parent)

    existing.add(base + "/")
    print(f"indexed {len(existing)} served paths (baseurl={base!r})")

    broken: dict[str, list[str]] = defaultdict(list)
    checked = 0

    for html_file in sorted(SITE.rglob("*.html")):
        if "_screenshots" in str(html_file):
            continue
        content = html_file.read_text(errors="replace")
        # Strip <script> blocks before extracting refs — they often
        # contain JS-concatenated pseudo-URLs like `' + url + '` that
        # are not real links.
        content = re.sub(r'<script[^>]*>.*?</script>', '', content,
                         flags=re.DOTALL)
        page = str(html_file.relative_to(SITE))

        # Compute the served URL of this page, so relative hrefs can be
        # resolved. For index.html files, the served URL is the parent
        # directory with a trailing slash.
        if html_file.name == "index.html":
            page_url = base + "/" + str(html_file.parent.relative_to(SITE)) + "/"
            page_url = page_url.replace("//", "/")
        else:
            page_url = base + "/" + page

        for ref in re.findall(r'(?:href|src)="([^"]+)"', content):
            checked += 1
            if any(ref.startswith(p) for p in SKIP_PREFIXES):
                continue
            if any(p in ref for p in SKIP_PATTERNS):
                continue
            clean = ref.split("#")[0].split("?")[0]
            if not clean:
                continue
            if not clean.startswith("/"):
                # Relative href — resolve against the current page URL.
                # This catches bare-ID hrefs like `href="309"` inherited
                # from the Drupal source, which silently 404 on the new
                # site.
                clean = urljoin(page_url, clean)
            candidates = [clean, clean.rstrip("/") + "/",
                          clean + "index.html",
                          clean.rstrip("/") + "/index.html"]
            if not any(c in existing for c in candidates):
                broken[clean].append(page)

    print(f"checked {checked} refs\n")

    if broken:
        print(f"BROKEN: {len(broken)} targets\n")
        for target in sorted(broken):
            pages = broken[target]
            print(f"  {target}")
            for p in pages[:3]:
                print(f"    <- {p}")
            if len(pages) > 3:
                print(f"    (+{len(pages) - 3} more)")
        if strict:
            sys.exit(1)
    else:
        print("No broken links found.")


if __name__ == "__main__":
    main()
