#!/usr/bin/env python3
"""Visual + functional verification of the kansaibenkyou.net Jekyll site.

Builds the site, serves it locally, and uses Playwright (headless
Chromium) to navigate, interact, screenshot, and assert correctness.

Screenshots are saved to _site/_screenshots/ so they can be inspected
via Claude Code's image reader.

Usage
-----

    python3 tools/verify_site.py [--no-build] [--page PATH]

Options:

    --no-build   Skip the jekyll build step (use an existing _site/).
    --page PATH  Verify a single page instead of the default set.
                 PATH is relative to the site root, e.g.
                 "/conversations/01-with-the-landlord/".
"""

from __future__ import annotations

import argparse
import http.server
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

REPO = Path(__file__).resolve().parent.parent
SITE_DIR = REPO / "_site"
SCREENSHOT_DIR = SITE_DIR / "_screenshots"
PORT = 4123


def build_site() -> None:
    gemfile = REPO / "Gemfile"
    gemfile_tmp = REPO / "Gemfile.tmp"
    try:
        gemfile.rename(gemfile_tmp)
        subprocess.run(
            ["jekyll", "build"],
            cwd=str(REPO),
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        if gemfile_tmp.exists():
            gemfile_tmp.rename(gemfile)
    print(f"built _site/ ({sum(1 for _ in SITE_DIR.rglob('*') if _.is_file())} files)")


def start_server() -> http.server.HTTPServer:
    handler = http.server.SimpleHTTPRequestHandler
    os.chdir(str(SITE_DIR))
    server = http.server.HTTPServer(("127.0.0.1", PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def screenshot(page: Page, name: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  screenshot: {path.relative_to(REPO)}")
    return path


def verify_conversation(page: Page, path: str = "/conversations/01-with-the-landlord/") -> list[str]:
    """Verify a conversation page. Returns a list of failure messages (empty = pass)."""
    failures: list[str] = []
    url = f"http://127.0.0.1:{PORT}{path}"
    page.goto(url)
    page.wait_for_load_state("networkidle")

    slug = path.strip("/").replace("/", "_")

    screenshot(page, f"{slug}_01_initial")

    # Check page title.
    title = page.title()
    if "Kansaibenkyou" not in title:
        failures.append(f"title missing 'Kansaibenkyou': {title!r}")

    # Check stanza count.
    stanzas = page.locator("tr.skit-stanza")
    n = stanzas.count()
    if n < 1:
        failures.append(f"expected >=1 stanzas, got {n}")
    else:
        print(f"  stanzas: {n}")

    # Check initial visibility: skit-k visible, skit-s/e/g/w hidden.
    first_k = page.locator(".skit-k").first
    first_s = page.locator(".skit-s").first
    if not first_k.is_visible():
        failures.append("skit-k (Kansai) not visible by default")
    if first_s.is_visible():
        failures.append("skit-s (standard) should be hidden by default")

    # Toggle "Show standard" and verify it becomes visible.
    btn_s = page.locator(".skit-toggle[data-layer='s']")
    btn_s.click()
    page.wait_for_timeout(200)
    screenshot(page, f"{slug}_02_standard_on")
    if not first_s.is_visible():
        failures.append("skit-s not visible after clicking Show standard")

    # Toggle "Show English".
    btn_e = page.locator(".skit-toggle[data-layer='e']")
    btn_e.click()
    page.wait_for_timeout(200)
    screenshot(page, f"{slug}_03_standard_and_english")

    # Toggle "Show grammar" — verify (NNN ...) markers are gone.
    btn_g = page.locator(".skit-toggle[data-layer='g']")
    btn_g.click()
    page.wait_for_timeout(200)
    screenshot(page, f"{slug}_04_grammar_on")

    grammar_lines = page.locator(".skit-g")
    has_raw_marker = False
    for i in range(min(grammar_lines.count(), 5)):
        html = grammar_lines.nth(i).inner_html()
        if "(" in html and ")" in html:
            import re
            if re.search(r"\(\d+[^)]+\)", html):
                has_raw_marker = True
                break
    if has_raw_marker:
        failures.append("skit-g still has raw (NNN...) markers — skit.js link rendering may have failed")

    grammar_links = page.locator(".skit-g a.skit-link")
    n_links = grammar_links.count()
    if n_links < 1:
        failures.append(f"expected >=1 grammar <a> links, got {n_links}")
    else:
        print(f"  grammar links rendered: {n_links}")

    # Toggle "Show words".
    btn_w = page.locator(".skit-toggle[data-layer='w']")
    btn_w.click()
    page.wait_for_timeout(200)
    screenshot(page, f"{slug}_05_all_on")

    word_links = page.locator(".skit-w a.skit-link")
    n_wlinks = word_links.count()
    if n_wlinks < 1:
        failures.append(f"expected >=1 word <a> links, got {n_wlinks}")
    else:
        print(f"  word links rendered: {n_wlinks}")

    # Check audio element.
    audio = page.locator("audio")
    if audio.count() < 1:
        failures.append("no <audio> element found")
    else:
        src = audio.first.get_attribute("src") or ""
        if ".mp3" not in src:
            failures.append(f"audio src missing .mp3: {src!r}")
        else:
            print(f"  audio src: {src}")

    # Turn everything off again.
    btn_s.click()
    btn_e.click()
    btn_g.click()
    btn_w.click()
    page.wait_for_timeout(200)
    screenshot(page, f"{slug}_06_all_off")

    return failures


def verify_index(page: Page) -> list[str]:
    """Verify the front page."""
    failures: list[str] = []
    page.goto(f"http://127.0.0.1:{PORT}/")
    page.wait_for_load_state("networkidle")
    screenshot(page, "index")

    links = page.locator("a[href*='conversations']")
    if links.count() < 1:
        failures.append("index page has no conversation links")
    else:
        print(f"  conversation links on index: {links.count()}")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--page", type=str, default=None)
    args = parser.parse_args()

    os.chdir(str(REPO))

    if not args.no_build:
        print("building site...")
        build_site()

    print(f"serving _site/ on http://127.0.0.1:{PORT}")
    server = start_server()

    all_failures: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()

            if args.page:
                print(f"\nverifying {args.page}")
                all_failures.extend(verify_conversation(page, args.page))
            else:
                print("\nverifying index...")
                all_failures.extend(verify_index(page))

                print("\nverifying chapter 1...")
                all_failures.extend(verify_conversation(page))

            browser.close()
    finally:
        server.shutdown()

    print()
    if all_failures:
        print(f"FAILED — {len(all_failures)} issue(s):")
        for f in all_failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("PASSED — all checks OK")
        print(f"screenshots in {SCREENSHOT_DIR.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
