#!/usr/bin/env python3
"""Mothball HTML → YAML importer for multiple content types.

Scans _mothball/snapshot/node/ for nodes matching the requested content
type, extracts fields from the Drupal HTML, and writes LinkML-conforming
YAML to data/<type_plural>/.

Usage
-----

    python3 tools/import_content.py words              # 280 word entries
    python3 tools/import_content.py grammar_points      # 45 grammar points
    python3 tools/import_content.py real_conversations   # 36 real conversations
    python3 tools/import_content.py phonology_topics     # 16 phonology topics
    python3 tools/import_content.py pages                # 12 basic pages
    python3 tools/import_content.py all                  # everything

Parsing
-------

Uses BeautifulSoup with lxml backend to parse each Drupal node page into a
DOM. Extraction operates on the parsed tree rather than raw regex matches,
which is what makes it robust against the field-item nesting, empty rows,
and malformed <em> nesting present in the original WYSIWYG output.

Link rewriting
--------------

Every <a> and <img>/<audio> descendant of an extracted field has its href
or src rewritten in-place via NODE_URL_MAP (for intra-site links, including
bare-numeric-ID hrefs like `<a href="309">` which were the Drupal
convention for same-content-type cross-references) and for `../external/`
paths (which become `/assets/audio/` or `/assets/images/`).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

try:
    import pykakasi
    _KAKASI = pykakasi.kakasi()
except ImportError:
    _KAKASI = None

REPO = Path(__file__).resolve().parent.parent
NODE_DIR = REPO / "_mothball" / "snapshot" / "node"

# Drupal article-class → collection slug. The dynamic portion of
# NODE_URL_MAP is computed from this at import time by scanning the
# mothball.
ARTICLE_TO_COLLECTION = {
    "article-grammar-point": "grammar-points",
    "article-type-word": "words",
    "article-real-conversation": "real-conversations",
    "article-phonology-topic": "phonology",
    "article-conversation-example": "example-conversations",
}

# Handcrafted overrides for Drupal pages that became site nav endpoints
# (e.g. node 1 = /what/, node 4 = /). These take precedence over the
# collection-based auto-mapping.
NODE_URL_OVERRIDES: dict[int, str] = {
    1: '/what/', 2: '/about/', 3: '/resources/', 4: '/',
    340: '/phonology/340/', 349: '/phonology/349/',
    350: '/phonology/350/', 351: '/phonology/351/',
    352: '/phonology/352/', 353: '/phonology/353/',
    354: '/phonology/354/', 357: '/example-conversations/',
    358: '/grammar/', 359: '/pronunciation/',
    360: '/phonology/360/', 366: '/bibliography/',
    387: '/real-conversations/', 388: '/phonology/388/',
    389: '/phonology/389/', 390: '/phonology/390/',
    391: '/phonology/391/', 392: '/phonology/392/',
    393: '/phonology/393/', 394: '/phonology/394/',
    395: '/phonology/395/', 396: '/copyright/',
    398: '/development/', 414: '/intro/',
}

CONTENT_TYPE_CLASSES = {
    "words": "article-type-word",
    "grammar_points": "article-grammar-point",
    "real_conversations": "article-real-conversation",
    "phonology_topics": "article-phonology-topic",
    "pages": "article-type-page",
}

ATTR_ASSIGN_RE = re.compile(r"[A-Za-z_:][-A-Za-z0-9_:.]*\s*=")

# Old-site relative paths that appear inside page / page-body HTML
# (e.g. <a href="../grammar-point-list">). These must be rewritten to
# the canonical new-site URLs so the cross-reference weave survives
# the Drupal → Jekyll transplant.
RELATIVE_PATH_MAP: dict[str, str] = {
    "about": "/about/",
    "bibliography": "/bibliography/",
    "blog": "/resources/",  # no blog section on the rebuild
    "common-use-list": "/common-use-list/",
    "copyright": "/copyright/",
    "development": "/development/",
    "example-conversations": "/example-conversations/",
    "feedback": "/feedback/",
    "grammar": "/grammar/",
    "grammar-point-list": "/grammar-points/",
    "home": "/",
    "index.html": "/",
    "intro": "/intro/",
    "pronunciation": "/pronunciation/",
    "real-conversations": "/real-conversations/",
    "resources": "/resources/",
    "what": "/what/",
    "words-list-page": "/vocabulary/",
}

# Mapping from suitability-icon basename to the canonical short label,
# matching the existing hand-curated 37 word entries. See
# `data/words/word_99.yaml` for the shape.
SUITABILITY_LABELS: dict[str, str] = {
    "i-age.png": "age-specific",
    "i-female.png": "female speech",
    "i-formal.png": "formal",
    "i-male.png": "male speech",
    "i-warning.png": "potentially rude",
}


# ---------------------------------------------------------------------------
# NODE_URL_MAP construction
# ---------------------------------------------------------------------------


def build_node_url_map() -> dict[int, str]:
    """Scan the mothball, assign a canonical site URL to every node id.

    Seeds from NODE_URL_OVERRIDES (which wins for special slugs like /what/),
    then fills in collection URLs for every node whose article class matches
    ARTICLE_TO_COLLECTION.
    """
    node_map: dict[int, str] = dict(NODE_URL_OVERRIDES)
    for f in NODE_DIR.iterdir():
        if not f.name.isdigit():
            continue
        nid = int(f.name)
        if nid in node_map:
            continue
        try:
            content = f.read_text(errors="replace")
        except Exception:
            continue
        for article_class, slug in ARTICLE_TO_COLLECTION.items():
            if f"article {article_class}" in content:
                node_map[nid] = f"/{slug}/{nid}/"
                break
    return node_map


# ---------------------------------------------------------------------------
# DOM parsing + field extraction
# ---------------------------------------------------------------------------


def escape_inner_title_quotes(html: str) -> str:
    """Escape raw inner double quotes inside title="..." attributes.

    A handful of Drupal-rendered lexicon markers in the mothball use
    title="... "quoted text" ..." instead of &quot;. BeautifulSoup/lxml
    treats the first inner quote as the end of the attribute, which
    produces bogus attributes like `in=""` and mangles the <sup> tag.
    Normalize that original-data quirk before parsing the DOM.
    """
    pieces: list[str] = []
    pos = 0

    while True:
        start = html.find('title="', pos)
        if start == -1:
            pieces.append(html[pos:])
            return "".join(pieces)

        value_start = start + len('title="')
        pieces.append(html[pos:value_start])
        cursor = value_start

        while True:
            quote = html.find('"', cursor)
            if quote == -1:
                pieces.append(html[cursor:])
                return "".join(pieces)

            boundary = quote + 1
            while boundary < len(html) and html[boundary].isspace():
                boundary += 1

            if (
                boundary >= len(html)
                or html.startswith("/>", boundary)
                or html[boundary] == ">"
                or ATTR_ASSIGN_RE.match(html, boundary)
            ):
                pieces.append(html[cursor:quote + 1])
                pos = quote + 1
                break

            pieces.append(html[cursor:quote])
            pieces.append("&quot;")
            cursor = quote + 1


def parse_node(node_id: int) -> BeautifulSoup:
    html = (NODE_DIR / str(node_id)).read_text(errors="replace")
    html = escape_inner_title_quotes(html)
    return BeautifulSoup(html, "lxml")


def find_field(soup: BeautifulSoup, field_name: str):
    """Return the field element, matching any tag with the
    `field-name-{field_name}` class. Drupal uses both <div> and <section>
    depending on the field's label-placement setting."""
    return soup.find(class_=f"field-name-{field_name}")


def get_field_items(field_div) -> list:
    """Return every field-item div inside a field container.

    A Drupal field with multiple "values" (e.g. the Example section on
    grammar 311 has four tables, each rendered as its own field-item
    with class field-item-even/odd) stores each value in its own div;
    callers must concatenate them to reconstruct the authored content.
    """
    if field_div is None:
        return []
    items = field_div.find("div", class_="field-items")
    if items is None:
        return []
    return items.find_all("div", class_="field-item", recursive=False)


# ---------------------------------------------------------------------------
# Link rewriting
# ---------------------------------------------------------------------------


BARE_ID_RE = re.compile(r"^(\d+)$")
NODE_PATH_RE = re.compile(r"^/?node/(\d+)/?$")
TAXONOMY_HTML_RE = re.compile(r"(?:^|/)taxonomy/term/(\d+)\.html$")
EXTERNAL_MEDIA_RE = re.compile(
    r"^\.\./external/(.+\.(?:mp3|wav|ogg|jpg|jpeg|png|gif))$",
    re.IGNORECASE,
)
# Relative-path pattern inside page bodies: `../foo` or `../foo/bar`.
RELATIVE_PAGE_RE = re.compile(r"^\.\./([^?#]+?)/?(\?[^#]*)?(?:#.*)?$")
# Absolute old-site URLs that appear in authored link targets
# (e.g. href="http://kansaibenkyou.net/node/what") — these are old
# Drupal URLs that must be remapped to the rebuild's canonical paths.
OLD_SITE_URL_RE = re.compile(
    r"^https?://(?:www\.|static\.)?kansaibenkyou\.net/(?:node/)?([\w-]+)/?$",
    re.IGNORECASE,
)

AUDIO_EXTS = {".mp3", ".wav", ".ogg"}


def rewrite_links(subtree, node_url_map: dict[int, str]) -> None:
    """Rewrite hrefs and srcs inside a BeautifulSoup subtree, in place.

    Covers:
      * bare-integer hrefs (Drupal's same-content cross-refs, e.g. href="309")
      * /node/N and node/N hrefs
      * /taxonomy/term/N.html → /taxonomy/term/N/
      * ../external/*.(mp3|wav|ogg) → /assets/audio/*
      * ../external/*.(jpg|png|gif) → /assets/images/*
    """
    if subtree is None:
        return
    for a in subtree.find_all("a"):
        href = a.get("href", "")
        if not href:
            continue
        new = _rewrite_href(href, node_url_map)
        if new is not None:
            a["href"] = new
    for tag in subtree.find_all(["img", "audio", "source", "video"]):
        src = tag.get("src", "")
        if not src:
            continue
        new = _rewrite_media_src(src)
        if new is not None:
            tag["src"] = new


def _rewrite_href(href: str, node_url_map: dict[int, str]) -> str | None:
    # Separate path from fragment / query so `href="396#outline-1"`
    # (bare-ID with in-page anchor) maps to the correct page URL
    # plus the original fragment.
    path = href
    suffix = ""
    for sep in ("#", "?"):
        if sep in path:
            idx = path.index(sep)
            suffix = path[idx:] + suffix
            path = path[:idx]
    m = BARE_ID_RE.match(path)
    if m:
        nid = int(m.group(1))
        return node_url_map.get(nid, path) + suffix
    m = NODE_PATH_RE.match(path)
    if m:
        nid = int(m.group(1))
        return node_url_map.get(nid, path) + suffix
    m = TAXONOMY_HTML_RE.search(path)
    if m:
        return f"/taxonomy/term/{m.group(1)}/" + suffix
    m = EXTERNAL_MEDIA_RE.match(path)
    if m:
        fname = m.group(1)
        ext = os.path.splitext(fname)[1].lower()
        subdir = "audio" if ext in AUDIO_EXTS else "images"
        return f"/assets/{subdir}/{fname}" + suffix
    m = RELATIVE_PAGE_RE.match(path)
    if m:
        rel = m.group(1)
        # `../taxonomy/term/NNN.html` → canonical term URL.
        m2 = re.match(r"^taxonomy/term/(\d+)\.html$", rel)
        if m2:
            return f"/taxonomy/term/{m2.group(1)}/" + suffix
        # Known old-site page slugs → new-site canonical URL.
        key = rel.rstrip("/")
        if key in RELATIVE_PATH_MAP:
            return RELATIVE_PATH_MAP[key] + suffix
    m = OLD_SITE_URL_RE.match(path)
    if m:
        key = m.group(1).rstrip("/")
        if key in RELATIVE_PATH_MAP:
            return RELATIVE_PATH_MAP[key] + suffix
        # Fall back: if the slug is numeric (node/NNN) and we know
        # the ID, use the node URL map.
        if key.isdigit():
            nid = int(key)
            if nid in node_url_map:
                return node_url_map[nid] + suffix
    return None


def _rewrite_media_src(src: str) -> str | None:
    m = EXTERNAL_MEDIA_RE.match(src)
    if m:
        fname = m.group(1)
        ext = os.path.splitext(fname)[1].lower()
        subdir = "audio" if ext in AUDIO_EXTS else "images"
        return f"/assets/{subdir}/{fname}"
    return None


# ---------------------------------------------------------------------------
# Field-content extractors
# ---------------------------------------------------------------------------


def extract_title(soup: BeautifulSoup) -> tuple[str, str]:
    """Extract the Japanese title + the second title component (romaji
    for word/grammar nodes) from the page <title> tag."""
    t = soup.find("title")
    if t is None or not t.string:
        return "", ""
    full = t.string.strip()
    m = re.match(r"(.+?) \| Kansaibenkyou", full)
    if not m:
        return "", ""
    inner = m.group(1).strip()
    parts = inner.split(" / ", 1)
    ja = parts[0].strip()
    en = parts[1].strip() if len(parts) > 1 else ""
    return ja, en


def romaji_from(ja: str) -> str:
    """Hepburn romanization of a Japanese string via pykakasi.

    Used as a fallback when the Drupal <title> tag doesn't already
    carry a romaji form. Returns the empty string if pykakasi is not
    installed or the input is empty.
    """
    if not ja or _KAKASI is None:
        return ""
    parts = _KAKASI.convert(ja)
    return "".join(p.get("hepburn", "") for p in parts).strip()


def existing_yaml_string(path: Path, key: str) -> str:
    """Return an existing scalar string value from a generated YAML file."""
    if not path.exists():
        return ""
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return ""
    value = data.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def extract_html_field(soup: BeautifulSoup, field_name: str,
                       node_url_map: dict[int, str]) -> str:
    """Return the field's inner HTML with links rewritten and cruft stripped.

    Cruft stripped:
      * <sup class="lexicon-indicator">...</sup> (marks Drupal glossary refs)
      * <h2 class="field-label">...</h2> (Drupal-rendered field label)
      * empty <tr></tr>, empty <em></em>, empty <p></p>

    Returns the serialized inner HTML (children of the field-item div
    concatenated) or the empty string.
    """
    items = get_field_items(find_field(soup, field_name))
    if not items:
        return ""
    pieces: list[str] = []
    for item in items:
        # Drupal's rendered field label sometimes leaks inside the field
        # div when the label placement is "above" — we render our own
        # headings in the layout, so strip it.
        for lbl in item.find_all("h2", class_="field-label"):
            lbl.decompose()
        rewrite_links(item, node_url_map)
        tag_tables_by_caption(item)
        # Remove structurally-empty artifacts.
        for tag_name in ("tr", "em", "p", "span"):
            for el in item.find_all(tag_name):
                if not el.contents and not el.get_text(strip=True):
                    el.decompose()
        pieces.append("".join(str(c) for c in item.children))
    inner = "".join(pieces)
    # Collapse runs of whitespace between tags (not inside text).
    inner = re.sub(r">\s+<", "><", inner)
    inner = re.sub(r"\s+", " ", inner).strip()
    return inner


# Production-rule tables have a `<td>` that is purely a horizontal
# arrow (e.g. `行かない → 行かへん`). They're visually better rendered
# without data-table borders — see custom.css .kb-production-table.
# We detect the `<td>`, not `<th>`: the politeness-level table has
# `↑↓` inside a `<th>` but is a real data table with row labels and
# should keep full borders.
_PRODUCTION_ARROW_RE = re.compile(r"^[→←⇒⇐⟶⟵]+$")


def tag_tables_by_caption(root) -> None:
    for table in root.find_all("table"):
        is_production = False
        for td in table.find_all("td"):
            text = td.get_text().strip()
            if text and _PRODUCTION_ARROW_RE.match(text):
                is_production = True
                break
        if is_production:
            existing = table.get("class") or []
            if "kb-production-table" not in existing:
                table["class"] = existing + ["kb-production-table"]


def extract_text_field(soup: BeautifulSoup, field_name: str) -> str:
    """Plain-text extraction preserving paragraph and list structure.

    Converts <br>, </p>, </div>, </li>, </tr> to newlines; </td>/</th>
    to tabs; strips all other tags. Paragraphs are separated by blank
    lines so the downstream YAML literal block scalar preserves the
    paragraph structure. The layout can then choose to render the
    newlines as <br>, split into <p>s, or feed through markdownify.
    """
    items = get_field_items(find_field(soup, field_name))
    if not items:
        return ""
    # Work from the serialized HTML so tag boundaries become newlines.
    raw = "\n\n".join(
        "".join(str(c) for c in item.children) for item in items
    )
    # Turn paragraph-ish boundaries into blank lines first, so they
    # survive the subsequent whitespace collapse.
    raw = re.sub(r"<br\s*/?>\s*<br\s*/?>", "\n\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</p>", "\n\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</(?:div|section|article)>", "\n\n", raw,
                 flags=re.IGNORECASE)
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</(?:li|tr|h[1-6])>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</?(?:td|th)>", "\t", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", "", raw)
    # The lxml parser already unescapes entities when serialising as
    # a parsed tree, but double-check by decoding any literal &amp;-
    # style sequences left in.
    import html as html_mod
    raw = html_mod.unescape(raw)
    # Paragraph preservation: collapse runs of blank lines to exactly
    # one blank line; strip per-line whitespace.
    lines = [ln.strip() for ln in raw.splitlines()]
    out: list[str] = []
    for ln in lines:
        if ln:
            out.append(ln)
        elif out and out[-1] != "":
            out.append("")
    return "\n".join(out).strip()


def extract_page_body(soup: BeautifulSoup, node_url_map: dict[int, str]) -> str:
    """Extract `body` from a Drupal page node as HTML, preserving anchor
    links, definition lists, tables, headings, and images.

    The old site's page bodies are the navigational spine of the
    learning site — "Grammar point list" and "Common use list" on
    /grammar/, the textbook / website listings on /resources/, the
    taxonomy cross-refs in the intro — all of these are clickable `<a>`
    anchors inside `<dt>` or `<dd>` tags. A plain-text extraction
    destroys the cross-reference weave and turns each page into a
    pedagogical dead end. We keep the HTML structure and let the
    layout render it directly (no markdownify), with a baseurl-rewrite
    pass for the absolute paths we emit.
    """
    items = get_field_items(find_field(soup, "body"))
    if not items:
        return ""
    pieces: list[str] = []
    for item in items:
        for lbl in item.find_all("h2", class_="field-label"):
            lbl.decompose()
        rewrite_links(item, node_url_map)
        tag_tables_by_caption(item)
        # Remove structurally-empty artifacts so the rendered HTML
        # doesn't have stray `<p></p>` or `<span></span>` slots.
        for tag_name in ("p", "span", "em", "tr"):
            for el in item.find_all(tag_name):
                if not el.contents and not el.get_text(strip=True):
                    el.decompose()
        pieces.append("".join(str(c) for c in item.children))
    inner = "".join(pieces)
    inner = re.sub(r">\s+<", "><", inner)
    inner = re.sub(r"\s+", " ", inner).strip()
    return inner


def extract_term_ids(soup: BeautifulSoup, field_name: str) -> list[str]:
    """Return taxonomy term IDs referenced by a term-reference field."""
    field_div = find_field(soup, field_name)
    if field_div is None:
        return []
    ids: list[str] = []
    for a in field_div.find_all("a"):
        href = a.get("href", "")
        m = re.search(r"taxonomy/term/(\d+)", href)
        if m:
            ids.append(m.group(1))
    return ids


def extract_suitability(soup: BeautifulSoup) -> list[dict]:
    """Return a list of {icon, label} dicts from field-word-suitability."""
    field_div = find_field(soup, "field-word-suitability")
    if field_div is None:
        return []
    out: list[dict] = []
    for img in field_div.find_all("img"):
        src = img.get("src", "")
        icon = os.path.basename(src)
        if not icon:
            continue
        label = SUITABILITY_LABELS.get(icon)
        if label is None:
            # Unknown icon — fall back to the title attribute if present,
            # else the icon basename without extension.
            label = (img.get("title") or os.path.splitext(icon)[0]).strip()
        entry: dict = {"icon": icon, "label": label}
        tooltip = (img.get("title") or "").strip()
        if tooltip:
            entry["tooltip"] = tooltip
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Per-content-type importers
# ---------------------------------------------------------------------------


def import_word(node_id: int, node_url_map: dict[int, str]) -> dict:
    soup = parse_node(node_id)
    title_ja, title_romaji = extract_title(soup)
    if not title_romaji:
        title_romaji = romaji_from(title_ja)
    if not title_romaji:
        title_romaji = existing_yaml_string(
            REPO / "data" / "words" / f"word_{node_id}.yaml",
            "title_romaji",
        )

    entry: dict = {
        "id": f"word_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja,
    }
    if title_romaji:
        entry["title_romaji"] = title_romaji

    # Word bodies and commentaries carry inline <a> cross-references and
    # <sup class="lexicon-indicator"> glossary pointers that must survive;
    # extract as HTML, not as flattened text. Kana/kanji fields are
    # single-token and don't need HTML.
    body = extract_html_field(soup, "body", node_url_map)
    commentary = extract_html_field(soup, "field-word-commentary", node_url_map)
    example = extract_html_field(soup, "field-word-example", node_url_map)
    # 101 word nodes carry a Kansai-side kanji variant in this field
    # (e.g. word 24 = `子芋` for こいも). Single-token, no HTML.
    kanji = extract_text_field(soup, "field-word-kanji")
    standard_kana = extract_text_field(soup, "field-word-standard")
    standard_kanji = extract_text_field(soup, "field-word-standard-kanji")
    suitability = extract_suitability(soup)
    word_type_ids = extract_term_ids(soup, "field-word-type")

    if body:
        entry["body"] = body
    if commentary:
        entry["commentary"] = commentary
    if example:
        entry["example"] = example
    if kanji:
        entry["kanji"] = kanji
    if standard_kana:
        entry["standard_kana"] = standard_kana
    if standard_kanji:
        entry["standard_kanji"] = standard_kanji
    if suitability:
        entry["suitability"] = suitability
    if word_type_ids:
        entry["word_types"] = [f"wordtype_{i}" for i in word_type_ids]

    return entry


def import_grammar_point(node_id: int, node_url_map: dict[int, str]) -> dict:
    soup = parse_node(node_id)
    title_ja, title_romaji = extract_title(soup)
    if not title_romaji:
        title_romaji = romaji_from(title_ja)
    if not title_romaji:
        title_romaji = existing_yaml_string(
            REPO / "data" / "grammar_points" / f"grammar_{node_id}.yaml",
            "title_romaji",
        )

    # Grammar bodies carry inline anchors + lexicon-indicator glossary
    # pointers that must survive; extract as HTML, not flattened text.
    body = extract_html_field(soup, "body", node_url_map)
    commentary = extract_html_field(soup, "field-gp-commentary", node_url_map)
    example = extract_html_field(soup, "field-gp-example", node_url_map)
    formation = extract_html_field(soup, "field-gp-formation", node_url_map)
    formation_from_std = extract_html_field(
        soup, "field-gp-formation-from-std", node_url_map,
    )
    kansai_v_std = extract_html_field(
        soup, "field-gp-kansai-v-std", node_url_map,
    )
    func_ids = extract_term_ids(soup, "field-function-type")
    gram_ids = extract_term_ids(soup, "field-grammar-type")

    # If formation_from_standard is byte-identical to formation, drop it —
    # Drupal shared the field value on ~6 grammar points and carrying both
    # produces duplicate rendering.
    if formation_from_std and formation_from_std == formation:
        formation_from_std = ""

    entry: dict = {
        "id": f"grammar_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja,
    }
    if title_romaji:
        entry["title_romaji"] = title_romaji
    if body:
        entry["body"] = body
    if commentary:
        entry["commentary"] = commentary
    if example:
        entry["example"] = example
    if formation:
        entry["formation"] = formation
    if formation_from_std:
        entry["formation_from_standard"] = formation_from_std
    if kansai_v_std:
        entry["kansai_vs_standard"] = kansai_v_std
    if func_ids:
        entry["function_types"] = [f"function_{i}" for i in func_ids]
    if gram_ids:
        entry["grammar_types"] = [f"grammar_{i}" for i in gram_ids]

    return entry


def import_real_conversation(node_id: int, node_url_map: dict[int, str]) -> dict:
    soup = parse_node(node_id)
    title_ja, title_en = extract_title(soup)

    desc = extract_text_field(soup, "field-real-conv-desc")
    hint = extract_text_field(soup, "field-real-conv-hint")

    audio_field = find_field(soup, "field-real-conv-audio")
    audio_path = ""
    if audio_field is not None:
        for a in audio_field.find_all("a"):
            href = a.get("href", "")
            m = re.search(r"/([^/\"]+\.mp3)$", href)
            if m:
                audio_path = m.group(1)
                break

    speaker_ids = extract_term_ids(soup, "field-real-conv-tags")

    entry: dict = {
        "id": f"real_conversation_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja,
    }
    if title_en:
        entry["title_en"] = title_en
    if desc:
        entry["summary"] = desc
    if hint:
        entry["hint"] = hint
    if audio_path:
        entry["audio"] = {"path": audio_path}
    if speaker_ids:
        entry["speakers"] = [f"character_{i}" for i in speaker_ids]

    return entry


def import_phonology_topic(node_id: int, node_url_map: dict[int, str]) -> dict:
    soup = parse_node(node_id)
    title_ja, title_en = extract_title(soup)
    # Phonology topic bodies are the most structurally rich pages on
    # the site: multiple audio-player widgets, pronunciation-comparison
    # tables, left-image illustrations, lexicon-indicator glossary
    # pointers, and cross-reference anchors. Preserve as HTML.
    body = extract_html_field(soup, "body", node_url_map)

    entry: dict = {
        "id": f"phonology_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja,
    }
    if title_en:
        entry["title_en"] = title_en
    if body:
        entry["body"] = body

    return entry


def import_page(node_id: int, node_url_map: dict[int, str]) -> dict:
    soup = parse_node(node_id)
    title_ja, title_en = extract_title(soup)
    body = extract_page_body(soup, node_url_map)

    canonical = soup.find("link", rel="canonical")
    slug = ""
    if canonical is not None:
        href = canonical.get("href", "")
        m = re.search(r"/([^/]+)$", href.rstrip("/"))
        if m:
            slug = m.group(1)

    entry: dict = {
        "id": f"page_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja or title_en,
    }
    if title_en:
        entry["title_en"] = title_en
    if slug:
        entry["slug"] = slug
    if body:
        entry["body"] = body

    return entry


# ---------------------------------------------------------------------------
# YAML emission
# ---------------------------------------------------------------------------


class _LiteralBlock(str):
    """YAML string that should be emitted as a literal block scalar."""


def _literal_block_repr(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data),
                                   style="|")


yaml.add_representer(_LiteralBlock, _literal_block_repr)


def _prepare_for_yaml(entry: dict) -> dict:
    """Wrap multi-line string fields so they serialize as literal block
    scalars — preserves explicit paragraph breaks (blank lines) without
    YAML's flow-scalar folding collapsing them to single spaces."""
    out: dict = {}
    for k, v in entry.items():
        if isinstance(v, str) and "\n" in v:
            out[k] = _LiteralBlock(v)
        else:
            out[k] = v
    return out


def write_yaml(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prepared = _prepare_for_yaml(data)
    path.write_text(
        yaml.dump(
            prepared, allow_unicode=True, sort_keys=False, indent=2, width=100,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def discover_nodes(article_class: str) -> list[int]:
    """Find all node IDs in the mothball matching an article class."""
    node_ids: list[int] = []
    for f in NODE_DIR.iterdir():
        if not f.name.isdigit():
            continue
        try:
            content = f.read_text(errors="replace")
        except Exception:
            continue
        if f"article {article_class}" in content:
            node_ids.append(int(f.name))
    return sorted(node_ids)


def run_import(content_type: str, node_url_map: dict[int, str]) -> None:
    article_class = CONTENT_TYPE_CLASSES[content_type]
    node_ids = discover_nodes(article_class)
    print(f"\n{content_type}: found {len(node_ids)} nodes")

    out_dir = REPO / "data" / content_type

    type_to_handler = {
        "words": (import_word, "word"),
        "grammar_points": (import_grammar_point, "grammar"),
        "real_conversations": (import_real_conversation, "real_conversation"),
        "phonology_topics": (import_phonology_topic, "phonology"),
        "pages": (import_page, "page"),
    }

    handler, prefix = type_to_handler[content_type]
    for node_id in node_ids:
        entry = handler(node_id, node_url_map)
        out = out_dir / f"{prefix}_{node_id}.yaml"
        write_yaml(entry, out)

    print(f"  wrote {len(node_ids)} files to data/{content_type}/")


def main() -> None:
    args = sys.argv[1:] or ["all"]
    types = list(CONTENT_TYPE_CLASSES.keys()) if "all" in args else args

    for t in types:
        if t not in CONTENT_TYPE_CLASSES:
            print(f"unknown type: {t!r} (valid: {', '.join(CONTENT_TYPE_CLASSES)})")
            sys.exit(1)

    print("building node URL map from mothball...")
    node_url_map = build_node_url_map()
    print(f"  {len(node_url_map)} nodes mapped "
          f"(grammar: {sum(1 for v in node_url_map.values() if '/grammar-points/' in v)}, "
          f"words: {sum(1 for v in node_url_map.values() if '/words/' in v)}, "
          f"example-conv: {sum(1 for v in node_url_map.values() if '/example-conversations/' in v and v.endswith('/'))}, "
          f"real-conv: {sum(1 for v in node_url_map.values() if '/real-conversations/' in v and v != '/real-conversations/')}, "
          f"phonology: {sum(1 for v in node_url_map.values() if '/phonology/' in v and v != '/phonology/')})"
          )

    for t in types:
        run_import(t, node_url_map)


if __name__ == "__main__":
    main()
