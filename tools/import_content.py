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
"""

from __future__ import annotations

import html as html_mod
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
NODE_DIR = REPO / "_mothball" / "snapshot" / "node"

CONTENT_TYPE_CLASSES = {
    "words": "article-type-word",
    "grammar_points": "article-grammar-point",
    "real_conversations": "article-real-conversation",
    "phonology_topics": "article-phonology-topic",
    "pages": "article-type-page",
}


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
        if f'article {article_class}' in content:
            node_ids.append(int(f.name))
    return sorted(node_ids)


def extract_title(html: str) -> tuple[str, str]:
    """Extract Japanese title + English title from <title> tag."""
    m = re.search(r"<title>(.+?) \| Kansaibenkyou", html)
    if not m:
        return "", ""
    full = html_mod.unescape(m.group(1))
    parts = full.split(" / ", 1)
    return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""


def extract_text_field(html: str, field_name: str) -> str:
    """Extract a text field's content, stripping HTML to plain text."""
    pattern = rf'field-name-{re.escape(field_name)}[^>]*>.*?<div class="field-items">(.*?)</div>\s*</div>'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return ""
    raw = m.group(1)
    text = re.sub(r"<br\s*/?>", "\n", raw)
    text = re.sub(r"</(?:p|div|tr|li|h[1-6])>", "\n", text)
    text = re.sub(r"</?(?:td|th)>", "\t", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    return text.strip()


def extract_term_ids(html: str, field_name: str) -> list[str]:
    """Extract taxonomy term IDs from a term-reference field."""
    section = re.search(
        rf'field-name-{re.escape(field_name)}(.*?)</(?:section|div)>\s*(?:<(?:section|div)|</article>)',
        html, re.DOTALL,
    )
    if not section:
        return []
    return re.findall(r"taxonomy/term/(\d+)", section.group(1))


def import_word(node_id: int) -> dict:
    html = (NODE_DIR / str(node_id)).read_text(errors="replace")
    title_ja, title_en = extract_title(html)

    body = extract_text_field(html, "body")
    commentary = extract_text_field(html, "field-word-commentary")
    standard_kana = extract_text_field(html, "field-word-standard")
    standard_kanji = extract_text_field(html, "field-word-standard-kanji")
    word_type_ids = extract_term_ids(html, "field-word-type")

    entry: dict = {
        "id": f"word_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja,
    }
    if title_en:
        entry["title_en"] = title_en
    if body:
        entry["body"] = body
    if commentary:
        entry["commentary"] = commentary
    if standard_kana:
        entry["standard_kana"] = standard_kana
    if standard_kanji:
        entry["standard_kanji"] = standard_kanji
    if word_type_ids:
        entry["word_types"] = [f"wordtype_{i}" for i in word_type_ids]

    return entry


def import_grammar_point(node_id: int) -> dict:
    html = (NODE_DIR / str(node_id)).read_text(errors="replace")
    title_ja, title_en = extract_title(html)

    body = extract_text_field(html, "body")
    commentary = extract_text_field(html, "field-gp-commentary")
    example = extract_text_field(html, "field-gp-example")
    formation = extract_text_field(html, "field-gp-formation")
    formation_from_std = extract_text_field(html, "field-gp-formation-from-std")
    kansai_v_std = extract_text_field(html, "field-gp-kansai-v-std")
    func_ids = extract_term_ids(html, "field-function-type")
    gram_ids = extract_term_ids(html, "field-grammar-type")

    entry: dict = {
        "id": f"grammar_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja,
    }
    if title_en:
        entry["title_en"] = title_en
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


def import_real_conversation(node_id: int) -> dict:
    html = (NODE_DIR / str(node_id)).read_text(errors="replace")
    title_ja, title_en = extract_title(html)

    desc = extract_text_field(html, "field-real-conv-desc")
    hint = extract_text_field(html, "field-real-conv-hint")

    m = re.search(
        r'field-name-field-real-conv-audio.*?href="[^"]*?/([^/"]+\.mp3)"',
        html, re.DOTALL,
    )
    audio_path = m.group(1) if m else ""

    speaker_ids = extract_term_ids(html, "field-real-conv-tags")

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


def import_phonology_topic(node_id: int) -> dict:
    html = (NODE_DIR / str(node_id)).read_text(errors="replace")
    title_ja, title_en = extract_title(html)
    body = extract_text_field(html, "body")

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


def import_page(node_id: int) -> dict:
    html = (NODE_DIR / str(node_id)).read_text(errors="replace")
    title_ja, title_en = extract_title(html)
    body = extract_text_field(html, "body")

    m = re.search(r'<link rel="canonical" href="[^"]*?/([^/"]+)"', html)
    slug = m.group(1) if m else ""

    entry: dict = {
        "id": f"page_{node_id}",
        "drupal_node_id": node_id,
        "title": title_ja if title_ja else title_en,
    }
    if title_en:
        entry["title_en"] = title_en
    if slug:
        entry["slug"] = slug
    if body:
        entry["body"] = body

    return entry


def write_yaml(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            data, allow_unicode=True, sort_keys=False, indent=2, width=100,
        ),
        encoding="utf-8",
    )


def run_import(content_type: str) -> None:
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
        entry = handler(node_id)
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
        run_import(t)


if __name__ == "__main__":
    main()
