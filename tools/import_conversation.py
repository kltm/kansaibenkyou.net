#!/usr/bin/env python3
"""Mothball HTML conversation node → ConversationExample YAML importer.

Reads every example-conversation stanza directly from the mothball Drupal
HTML under `_mothball/snapshot/node/<id>`, including the five rendered
layers (kansai / standard / english / grammar / word) plus stage-direction
rows. Outputs ConversationExample YAML conforming to schema/kbnet.yaml.

Usage
-----

    python3 tools/import_conversation.py          # all 12 chapters
    python3 tools/import_conversation.py 1        # chapter 1 only
    python3 tools/import_conversation.py 3 7 12   # specific chapters

Writes to ``data/conversations/<base>.yaml``. Validate with:

    linkml-validate --schema schema/kbnet.yaml \\
        --target-class ConversationExample \\
        data/conversations/<base>.yaml
"""

from __future__ import annotations

import html as html_mod
import re
import sys
from pathlib import Path

import yaml
from bs4.element import NavigableString, Tag

from import_content import (
    extract_text_field,
    extract_title,
    find_field,
    get_field_items,
    parse_node,
)

REPO = Path(__file__).resolve().parent.parent
TAXONOMY_TERM_RE = re.compile(r"taxonomy/term/(\d+)")
NODE_ID_RE = re.compile(r"(?:^|/)(\d+)(?:/)?$")
WHITESPACE_RE = re.compile(r"\s+")

CHAPTERS: list[tuple[int, int, str]] = [
    (1, 264, "01.with_the_landlord"),
    (2, 265, "02.at_the_welcome_party"),
    (3, 266, "03.at_the_shops"),
    (4, 267, "04.at_the_fish_monger"),
    (5, 268, "05.asking_directions"),
    (6, 269, "06.at_karaoke"),
    (7, 270, "07.on_a_train"),
    (8, 271, "08.with_a_neighbor"),
    (9, 272, "09.at_work"),
    (10, 273, "10.on_a_break"),
    (11, 274, "11.at_a_pub"),
    (12, 275, "12.at_okonomiyaki"),
]


def normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", html_mod.unescape(value)).strip()


def extract_term_ids(soup, field_name: str) -> list[str]:
    field = find_field(soup, field_name)
    if field is None:
        return []
    term_ids: list[str] = []
    for anchor in field.find_all("a", href=True):
        match = TAXONOMY_TERM_RE.search(anchor["href"])
        if match:
            term_ids.append(match.group(1))
    return term_ids


def extract_metadata(soup) -> dict:
    """Parse metadata from a mothball Drupal conversation node DOM."""
    title_ja, title_en = extract_title(soup)
    desc = extract_text_field(soup, "field-conv-exp-desc")

    audio_field = find_field(soup, "field-conv-exp-audio")
    audio_link = audio_field.find("a", href=True) if audio_field else None
    audio = audio_link["href"].rsplit("/", 1)[-1] if audio_link else ""

    char_ids = extract_term_ids(soup, "field-conv-exp-tags")
    func_ids = extract_term_ids(soup, "field-function-type")
    gram_ids = extract_term_ids(soup, "field-grammar-type")

    return {
        "title": title_ja,
        "title_en": title_en,
        "summary": desc,
        "audio_path": audio,
        "characters": [f"character_{i}" for i in char_ids],
        "function_types": [f"function_{i}" for i in func_ids],
        "grammar_types": [f"grammar_{i}" for i in gram_ids],
    }


def annotation_from_tag(tag: Tag) -> str:
    href = tag.get("href", "")
    text = "".join(stringify_node(child) for child in tag.children)
    match = NODE_ID_RE.search(href)
    if match:
        return f"({match.group(1)}{text})"
    return text


def stringify_node(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return str(node)
    if node.name == "a":
        return annotation_from_tag(node)
    if node.name == "br":
        return "\n"
    return "".join(stringify_node(child) for child in node.children)


def strip_speaker_punctuation(text: str) -> str:
    return text.strip().rstrip("：:")


def extract_stanza_row(row: Tag) -> tuple[str, dict[str, str]]:
    if row.select_one("li.skit-k"):
        speaker_cell = row.select_one("td.skit-name")
        speaker = strip_speaker_punctuation(
            speaker_cell.get_text(" ", strip=True) if speaker_cell else ""
        )

        line_map: dict[str, str] = {}
        for css_class, field_name in (
            ("skit-k", "kansai"),
            ("skit-s", "standard"),
            ("skit-e", "english"),
            ("skit-g", "kansai_grammar"),
            ("skit-w", "kansai_word"),
        ):
            line = row.select_one(f"li.{css_class}")
            if line is None:
                raise ValueError(
                    f"missing {css_class} stanza layer for speaker {speaker!r}"
                )
            line_map[field_name] = normalize_text(stringify_node(line))

        return speaker, line_map

    cells = row.find_all("td", recursive=False)
    if len(cells) == 1:
        stage_text = normalize_text(cells[0].get_text(" ", strip=True))
        return "", {
            "kansai": stage_text,
            "standard": stage_text,
            "english": stage_text,
            "kansai_grammar": "",
            "kansai_word": "",
        }

    raise ValueError("unexpected conversation stanza row structure")


def extract_stanzas(soup) -> list[dict]:
    body_field = find_field(soup, "body")
    body_items = get_field_items(body_field)
    if not body_items:
        return []

    table = body_items[0].select_one("#skit-template table")
    if table is None:
        return []

    stanzas: list[dict] = []
    for row in table.find_all("tr"):
        speaker, line_map = extract_stanza_row(row)
        stanza: dict = {
            "speaker": speaker,
            "kansai": line_map["kansai"],
            "standard": line_map["standard"],
            "english": line_map["english"],
        }
        if (
            line_map["kansai_grammar"]
            and line_map["kansai_grammar"] != line_map["kansai"]
        ):
            stanza["kansai_grammar"] = line_map["kansai_grammar"]
        if (
            line_map["kansai_word"]
            and line_map["kansai_word"] != line_map["kansai"]
        ):
            stanza["kansai_word"] = line_map["kansai_word"]
        stanzas.append(stanza)

    return stanzas


def build_conversation(
    _ch_num: int, node_id: int, base: str
) -> tuple[dict, Path]:
    """Build a ConversationExample dict from mothball HTML."""
    soup = parse_node(node_id)
    meta = extract_metadata(soup)
    stanzas = extract_stanzas(soup)

    conv: dict = {
        "id": f"conversation_{node_id}",
        "drupal_node_id": node_id,
        "title": meta["title"],
        "title_en": meta["title_en"],
        "summary": meta["summary"],
        "characters": meta["characters"],
        "audio": {"path": meta["audio_path"]},
        "stanzas": stanzas,
        "function_types": meta["function_types"],
        "grammar_types": meta["grammar_types"],
    }

    slug = base.replace(".", "_", 1)
    out = REPO / "data" / "conversations" / f"{slug}.yaml"
    return conv, out


def main() -> None:
    if len(sys.argv) > 1:
        requested = {int(a) for a in sys.argv[1:]}
        chapters = [(n, nid, b) for n, nid, b in CHAPTERS if n in requested]
    else:
        chapters = CHAPTERS

    out_dir = REPO / "data" / "conversations"
    out_dir.mkdir(parents=True, exist_ok=True)

    for ch_num, node_id, base in chapters:
        conv, out = build_conversation(ch_num, node_id, base)
        out.write_text(
            yaml.safe_dump(
                conv,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
                width=100,
            ),
            encoding="utf-8",
        )
        print(
            f"ch{ch_num:>2d}  node/{node_id}  "
            f"{len(conv['stanzas']):>3d} stanzas  → {out.name}"
        )


if __name__ == "__main__":
    main()
