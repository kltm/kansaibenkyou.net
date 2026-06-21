#!/usr/bin/env python3
"""Paired old-vs-new screenshots for manual visual fidelity review.

For each representative page — one per content type — this script
captures two screenshots with Playwright:

    * the old site at https://legacy.kansaibenkyou.net/...
    * the local new site at http://127.0.0.1:4000/kansaibenkyou.net/...

Screenshots land in `_site/_screenshots/ab/` with a matching pair of
`<slug>_old.png` and `<slug>_new.png`, plus an `index.html` that
displays the pairs side-by-side at a viewport-native size.

This is deliberately a human-facing tool: automated pixel diffing would
be noise-heavy (MM typography and palette diverge on purpose), so we
stop short of machine comparison and let a reviewer (or a vision-model
agent wrapping this output) pick out the pedagogical features that
went missing.

Usage:

    # With the local site running at 127.0.0.1:4000 already:
    python3 tools/visual_ab.py
    # Then open _site/_screenshots/ab/index.html in a browser.

    python3 tools/visual_ab.py --only grammar_311,page_grammar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
# Keep the output outside _site/ so Jekyll's auto-regeneration
# doesn't wipe it between captures.
OUT = REPO / "screenshots" / "ab"

# The 2016 mothball, re-hosted in genkisugi after the kb AWS account was
# wound down (static.kansaibenkyou.net retired). Byte-identical content.
OLD_BASE = "https://legacy.kansaibenkyou.net"
NEW_BASE = "http://127.0.0.1:4000/kansaibenkyou.net"

# Representative page per content type. Picked to exercise the
# features most likely to have been stripped during import: heavy
# cross-referencing, tables, the lexicon `?` glyph, audio widgets,
# definition lists.
PAIRS: list[tuple[str, str, str, str]] = [
    # (slug,            description,                old-site path,                            new-site path)
    ("grammar_311",    "Grammar point (yan/yanka/yanke/gana)",
     "/node/311",                                  "/grammar-points/311/"),
    ("grammar_296",    "Grammar point (V-hen/V-n negative)",
     "/node/296",                                  "/grammar-points/296/"),
    ("word_24",        "Word page — has anchor+lexicon cross-refs",
     "/node/24",                                   "/words/24/"),
    ("word_99",        "Word page — anjou, has suitability icons",
     "/node/99",                                   "/words/99/"),
    ("conv_264",       "Example conversation (01, with-the-landlord)",
     "/node/264",                                  "/example-conversations/01-with-the-landlord/"),
    ("realconv_376",   "Real conversation",
     "/node/376",                                  "/real-conversations/376/"),
    ("phono_340",      "Phonology topic — heavy loss (audio+tables+anchors)",
     "/node/340",                                  "/phonology/340/"),
    ("phono_391",      "Phonology topic — most-affected (44 anchors, 38 audio)",
     "/node/391",                                  "/phonology/391/"),
    ("term_154",       "Taxonomy term with glossary definition",
     "/taxonomy/term/154",                         "/taxonomy/term/154/"),
    ("page_grammar",   "/grammar/ hub page",
     "/node/358",                                  "/grammar/"),
    ("page_intro",     "/intro/ hub page (dense dt/dd structure)",
     "/node/414",                                  "/intro/"),
    ("page_resources", "/resources/ hub page (textbook listings)",
     "/node/3",                                    "/resources/"),
    ("homepage",       "Homepage",
     "/",                                          "/"),
]

VIEWPORT = {"width": 1280, "height": 1600}


def capture(page, url: str, out_path: Path) -> tuple[bool, str]:
    """Return (success, message). Saves a full-page screenshot."""
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        return False, f"goto failed: {type(e).__name__}: {e}"
    # Give dynamic content (banner rotation, Pagefind init) a moment
    # to settle, but don't block on the whole of JS land.
    page.wait_for_timeout(400)
    try:
        page.screenshot(path=str(out_path), full_page=True)
    except Exception as e:
        return False, f"screenshot failed: {e}"
    return True, ""


def write_index(pairs: list[tuple[str, str, str, str]]) -> None:
    """Emit a side-by-side HTML index of all captured pairs."""
    rows = []
    for slug, desc, old_path, new_path in pairs:
        old_img = f"{slug}_old.png"
        new_img = f"{slug}_new.png"
        old_exists = (OUT / old_img).exists()
        new_exists = (OUT / new_img).exists()
        old_cell = (f'<img src="{old_img}" loading="lazy" alt="old {slug}" />'
                    if old_exists else '<div class="missing">—</div>')
        new_cell = (f'<img src="{new_img}" loading="lazy" alt="new {slug}" />'
                    if new_exists else '<div class="missing">—</div>')
        rows.append(f"""
      <tr id="{slug}">
        <td class="label">
          <h2>{slug}</h2>
          <p>{desc}</p>
          <p><small><a href="{OLD_BASE}{old_path}" target="_blank">old</a>
            &middot;
            <a href="{NEW_BASE}{new_path}" target="_blank">new</a></small></p>
        </td>
        <td class="pane">
          <div class="caption">OLD — {old_path}</div>
          {old_cell}
        </td>
        <td class="pane">
          <div class="caption">NEW — {new_path}</div>
          {new_cell}
        </td>
      </tr>""")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Visual A/B — Kansaibenkyou.net</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 1rem;
          background: #2a2a2a; color: #eee; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td {{ vertical-align: top; padding: 0.5rem; border-bottom: 1px solid #444; }}
  td.label {{ width: 200px; background: #1e1e1e; }}
  td.pane {{ width: 50%; background: #111; }}
  img {{ max-width: 100%; border: 1px solid #444; }}
  .caption {{ font-family: monospace; font-size: 0.85em; color: #aaa;
              margin-bottom: 0.3rem; }}
  .missing {{ color: #c66; font-style: italic; padding: 2rem; }}
  h1 {{ margin-top: 0; }}
  h2 {{ font-size: 1rem; margin: 0 0 0.3rem; color: #fff; }}
  p {{ margin: 0.15rem 0; color: #ccc; font-size: 0.9em; }}
  a {{ color: #8cf; }}
</style>
</head>
<body>
<h1>Visual A/B: old vs new site</h1>
<p>Left column: <a href="{OLD_BASE}">legacy.kansaibenkyou.net</a>.
Right column: local new-site build at
<code>{NEW_BASE}</code>. Typography, palette, and chrome are expected to
differ; look for <strong>pedagogical features</strong> present on the left
but absent or degraded on the right — `?` glossary markers, cross-reference
links, audio players, tables, dt/dd definition listings.</p>
<table>
{''.join(rows)}
</table>
</body>
</html>
"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default="",
                        help="comma-separated slugs to capture")
    parser.add_argument("--skip-old", action="store_true",
                        help="don't re-fetch the old site (use cached)")
    parser.add_argument("--skip-new", action="store_true",
                        help="don't re-fetch the new site")
    args = parser.parse_args()

    only = set(s.strip() for s in args.only.split(",") if s.strip())
    todo = [p for p in PAIRS if not only or p[0] in only]
    if not todo:
        print("no pairs match --only filter")
        sys.exit(2)

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"capturing {len(todo)} pair(s) into {OUT.relative_to(REPO)}/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT,
                                   user_agent=("Mozilla/5.0 (Visual-AB/1.0) "
                                                "PlaywrightChromium"))
        page = ctx.new_page()

        for slug, desc, old_path, new_path in todo:
            print(f"\n{slug}: {desc}")
            old_out = OUT / f"{slug}_old.png"
            new_out = OUT / f"{slug}_new.png"
            if not args.skip_old:
                ok, msg = capture(page, OLD_BASE + old_path, old_out)
                status = "OK" if ok else f"FAIL ({msg})"
                print(f"  OLD {OLD_BASE}{old_path}  -> {status}")
            if not args.skip_new:
                ok, msg = capture(page, NEW_BASE + new_path, new_out)
                status = "OK" if ok else f"FAIL ({msg})"
                print(f"  NEW {NEW_BASE}{new_path}  -> {status}")

        browser.close()

    write_index(PAIRS)
    idx_path = OUT / "index.html"
    print(f"\nindex written: {idx_path.relative_to(REPO)}")
    print(f"open: file://{idx_path}")


if __name__ == "__main__":
    main()
