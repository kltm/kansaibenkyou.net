#!/usr/bin/env python3
"""Report text drift between imported YAML content and mothball source HTML.

This checker complements tools/check_source_fidelity.py:
it compares the actual imported text-bearing fields, not just structural
feature counts. Source extraction intentionally mirrors the current importer
logic so that required rewrites (for example, canonicalized internal links)
do not drown out real content drift.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from import_content import (
    REPO,
    build_node_url_map,
    extract_html_field,
    extract_page_body,
    extract_text_field,
    extract_title,
    find_field,
    get_field_items,
    parse_node,
)

DATA = REPO / "data"
TRAILING_EMPTY_P_RE = re.compile(
    r"(?:\s*<p(?:\s+[^>]*)?>\s*(?:<br\s*/?>\s*)?</p>\s*)+$",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
NODE_ID_RE = re.compile(r"(?:^|/)(\d+)(?:/)?$")
ANNOTATION_RE = re.compile(r"\((\d+)([^()]*)\)")

TEXT_FIELD_ORDER: dict[str, list[str]] = {
    "grammar_points": [
        "title",
        "body",
        "commentary",
        "example",
        "formation",
        "formation_from_standard",
        "kansai_vs_standard",
    ],
    "words": [
        "title",
        "body",
        "commentary",
        "example",
        "standard_kana",
        "standard_kanji",
        "kanji",
    ],
    "real_conversations": [
        "title",
        "summary",
        "hint",
        "useful_expressions",
    ],
    "conversations": [
        "title",
        "summary",
    ],
    "phonology_topics": [
        "title",
        "body",
    ],
    "pages": [
        "title",
        "body",
    ],
}


@dataclass
class Drift:
    content_type: str
    node_id: int
    field: str
    source_text: str
    yaml_text: str
    summary: str


def normalize(value: str | None) -> str:
    """Normalize comparison noise while preserving authored text."""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = html.unescape(text)
    text = BR_RE.sub("<br/>", text)
    text = TRAILING_EMPTY_P_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def canonicalize_attr_order(value: str) -> str:
    """Return HTML with attributes sorted for diff classification."""
    if "<" not in value or ">" not in value:
        return normalize(value)
    soup = BeautifulSoup(f"<div>{value}</div>", "lxml")
    for tag in soup.find_all(True):
        if not tag.attrs:
            continue
        attrs: dict[str, object] = {}
        for key in sorted(tag.attrs):
            attr_value = tag.attrs[key]
            if isinstance(attr_value, list):
                attrs[key] = " ".join(attr_value)
            else:
                attrs[key] = attr_value
        tag.attrs = attrs
    wrapper = soup.find("div")
    inner = "".join(str(child) for child in wrapper.children) if wrapper else value
    return normalize(inner)


def strip_markup(value: str) -> str:
    """Reduce HTML-bearing values to visible text for classification."""
    plain = ANNOTATION_RE.sub(r"\2", value)
    if "<" in plain and ">" in plain:
        soup = BeautifulSoup(f"<div>{plain}</div>", "lxml")
        wrapper = soup.find("div")
        plain = wrapper.get_text(" ", strip=False) if wrapper else plain
    return normalize(plain)


def snippet(text: str, limit: int = 40) -> str:
    compact = normalize(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def summarize_diff(source_text: str, yaml_text: str) -> str:
    """Return a short human-readable explanation of the difference."""
    if canonicalize_attr_order(source_text) == canonicalize_attr_order(yaml_text):
        return "attribute reordering only"

    source_visible = strip_markup(source_text)
    yaml_visible = strip_markup(yaml_text)
    if source_visible == yaml_visible:
        return "markup differs; text identical"

    if source_visible and yaml_visible:
        prefix = 0
        max_prefix = min(len(source_visible), len(yaml_visible))
        while prefix < max_prefix and source_visible[prefix] == yaml_visible[prefix]:
            prefix += 1

        suffix = 0
        max_suffix = min(
            len(source_visible) - prefix,
            len(yaml_visible) - prefix,
        )
        while (
            suffix < max_suffix
            and source_visible[-(suffix + 1)] == yaml_visible[-(suffix + 1)]
        ):
            suffix += 1

        if suffix:
            source_delta = source_visible[prefix:-suffix]
            yaml_delta = yaml_visible[prefix:-suffix]
        else:
            source_delta = source_visible[prefix:]
            yaml_delta = yaml_visible[prefix:]

        source_delta = snippet(source_delta or source_visible)
        yaml_delta = snippet(yaml_delta or yaml_visible)
        if source_delta and yaml_delta:
            return f"{source_delta} → {yaml_delta}"

    return "text content differs"


def format_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "\\n")


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not load as a mapping")
    return data


def compare_field(
    drifts: list[Drift],
    content_type: str,
    node_id: int,
    field: str,
    source_value: str | None,
    yaml_value: str | None,
) -> None:
    source_text = normalize(source_value)
    yaml_text = normalize(yaml_value)
    if source_text == yaml_text:
        return
    drifts.append(
        Drift(
            content_type=content_type,
            node_id=node_id,
            field=field,
            source_text=source_text,
            yaml_text=yaml_text,
            summary=summarize_diff(source_text, yaml_text),
        )
    )


def extract_page_title(soup: BeautifulSoup) -> str:
    title_ja, title_en = extract_title(soup)
    return title_ja or title_en


def extract_source_fields(
    content_type: str,
    yaml_data: dict,
    node_url_map: dict[int, str],
) -> list[tuple[str, str | None, str | None]]:
    node_id = int(yaml_data["drupal_node_id"])
    soup = parse_node(node_id)

    if content_type == "grammar_points":
        source_fields = [
            ("title", extract_title(soup)[0], yaml_data.get("title")),
            ("body", extract_html_field(soup, "body", node_url_map), yaml_data.get("body")),
            (
                "commentary",
                extract_html_field(soup, "field-gp-commentary", node_url_map),
                yaml_data.get("commentary"),
            ),
            (
                "example",
                extract_html_field(soup, "field-gp-example", node_url_map),
                yaml_data.get("example"),
            ),
            (
                "formation",
                extract_html_field(soup, "field-gp-formation", node_url_map),
                yaml_data.get("formation"),
            ),
            (
                "formation_from_standard",
                extract_html_field(soup, "field-gp-formation-from-std", node_url_map),
                yaml_data.get("formation_from_standard"),
            ),
            (
                "kansai_vs_standard",
                extract_html_field(soup, "field-gp-kansai-v-std", node_url_map),
                yaml_data.get("kansai_vs_standard"),
            ),
        ]
        source_map = {field: value for field, value, _ in source_fields}
        if (
            source_map["formation_from_standard"]
            and source_map["formation_from_standard"] == source_map["formation"]
        ):
            source_map["formation_from_standard"] = ""
        return [
            (field, source_map[field], yaml_value)
            for field, _, yaml_value in source_fields
        ]

    if content_type == "words":
        return [
            ("title", extract_title(soup)[0], yaml_data.get("title")),
            ("body", extract_html_field(soup, "body", node_url_map), yaml_data.get("body")),
            (
                "commentary",
                extract_html_field(soup, "field-word-commentary", node_url_map),
                yaml_data.get("commentary"),
            ),
            (
                "example",
                extract_html_field(soup, "field-word-example", node_url_map),
                yaml_data.get("example"),
            ),
            (
                "standard_kana",
                extract_text_field(soup, "field-word-standard"),
                yaml_data.get("standard_kana"),
            ),
            (
                "standard_kanji",
                extract_text_field(soup, "field-word-standard-kanji"),
                yaml_data.get("standard_kanji"),
            ),
            (
                "kanji",
                extract_text_field(soup, "field-word-kanji"),
                yaml_data.get("kanji"),
            ),
        ]

    if content_type == "real_conversations":
        return [
            ("title", extract_title(soup)[0], yaml_data.get("title")),
            (
                "summary",
                extract_text_field(soup, "field-real-conv-desc"),
                yaml_data.get("summary"),
            ),
            (
                "hint",
                extract_text_field(soup, "field-real-conv-hint"),
                yaml_data.get("hint"),
            ),
            (
                "useful_expressions",
                extract_html_field(soup, "field-real-conv-expr", node_url_map),
                yaml_data.get("useful_expressions"),
            ),
        ]

    if content_type == "phonology_topics":
        return [
            ("title", extract_title(soup)[0], yaml_data.get("title")),
            ("body", extract_html_field(soup, "body", node_url_map), yaml_data.get("body")),
        ]

    if content_type == "pages":
        return [
            ("title", extract_page_title(soup), yaml_data.get("title")),
            ("body", extract_page_body(soup, node_url_map), yaml_data.get("body")),
        ]

    if content_type == "conversations":
        return extract_conversation_fields(soup, yaml_data)

    raise ValueError(f"unknown content type: {content_type}")


def annotation_from_tag(tag: Tag) -> str:
    href = tag.get("href", "")
    match = NODE_ID_RE.search(href)
    text = "".join(stringify_node(child) for child in tag.children)
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


def extract_conversation_row(row: Tag) -> tuple[str, dict[str, str]]:
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
            line_map[field_name] = stringify_node(line).strip() if line else ""
        if line_map["kansai_grammar"] == line_map["kansai"]:
            line_map["kansai_grammar"] = ""
        if line_map["kansai_word"] == line_map["kansai"]:
            line_map["kansai_word"] = ""
        return speaker, line_map

    cells = row.find_all("td", recursive=False)
    if len(cells) == 1:
        stage_text = cells[0].get_text(" ", strip=True)
        return "", {
            "kansai": stage_text,
            "standard": stage_text,
            "english": stage_text,
            "kansai_grammar": "",
            "kansai_word": "",
        }

    return "", {
        "kansai": "",
        "standard": "",
        "english": "",
        "kansai_grammar": "",
        "kansai_word": "",
    }


def extract_conversation_fields(
    soup: BeautifulSoup,
    yaml_data: dict,
) -> list[tuple[str, str | None, str | None]]:
    fields: list[tuple[str, str | None, str | None]] = [
        ("title", extract_title(soup)[0], yaml_data.get("title")),
        (
            "summary",
            extract_text_field(soup, "field-conv-exp-desc"),
            yaml_data.get("summary"),
        ),
    ]

    yaml_stanzas = yaml_data.get("stanzas") or []
    if not isinstance(yaml_stanzas, list):
        yaml_stanzas = []

    body_field = find_field(soup, "body")
    body_items = get_field_items(body_field)
    if not body_items:
        source_rows: list[Tag] = []
    else:
        container = BeautifulSoup(str(body_items[0]), "lxml")
        table = container.select_one("#skit-template table")
        source_rows = table.find_all("tr") if table else []

    max_rows = max(len(source_rows), len(yaml_stanzas))
    fields.append(("stanzas.count", str(len(source_rows)), str(len(yaml_stanzas))))

    for index in range(max_rows):
        stanza_num = f"{index + 1:02d}"
        yaml_stanza = yaml_stanzas[index] if index < len(yaml_stanzas) else {}
        if not isinstance(yaml_stanza, dict):
            yaml_stanza = {}

        if index < len(source_rows):
            _speaker, line_map = extract_conversation_row(source_rows[index])
            del _speaker
        else:
            line_map = {
                "kansai": "",
                "standard": "",
                "english": "",
                "kansai_grammar": "",
                "kansai_word": "",
            }

        for field_name in ("kansai", "standard", "english", "kansai_grammar", "kansai_word"):
            fields.append(
                (
                    f"stanzas[{stanza_num}].{field_name}",
                    line_map[field_name],
                    yaml_stanza.get(field_name),
                )
            )

    return fields


def scan_content_type(content_type: str, node_url_map: dict[int, str]) -> list[Drift]:
    data_dir = DATA / content_type
    yaml_paths = sorted(data_dir.glob("*.yaml"))
    drifts: list[Drift] = []

    for yaml_path in yaml_paths:
        yaml_data = load_yaml(yaml_path)
        node_id = int(yaml_data["drupal_node_id"])
        for field, source_value, yaml_value in extract_source_fields(
            content_type,
            yaml_data,
            node_url_map,
        ):
            compare_field(drifts, content_type, node_id, field, source_value, yaml_value)

    field_order = {name: index for index, name in enumerate(TEXT_FIELD_ORDER[content_type])}

    def sort_key(drift: Drift) -> tuple[int, int, str]:
        base = drift.field.split(".", 1)[0]
        if base.startswith("stanzas["):
            return (drift.node_id, 9999, drift.field)
        return (drift.node_id, field_order.get(base, 9999), drift.field)

    drifts.sort(key=sort_key)
    return drifts


def print_report(all_drifts: dict[str, list[Drift]], quiet: bool) -> None:
    for content_type in TEXT_FIELD_ORDER:
        drifts = all_drifts.get(content_type, [])
        node_count = len({drift.node_id for drift in drifts})
        print(f"{content_type}: {len(drifts)} drifts across {node_count} nodes")
        if quiet:
            continue
        for drift in drifts:
            print(
                f"{drift.content_type} {drift.node_id} {drift.field} | "
                f"{format_cell(drift.source_text)} | "
                f"{format_cell(drift.yaml_text)} | "
                f"{drift.summary}"
            )
        if content_type != list(TEXT_FIELD_ORDER)[-1]:
            print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print per-type summary lines only",
    )
    args = parser.parse_args()

    node_url_map = build_node_url_map()
    all_drifts: dict[str, list[Drift]] = {}
    total = 0

    for content_type in TEXT_FIELD_ORDER:
        drifts = scan_content_type(content_type, node_url_map)
        all_drifts[content_type] = drifts
        total += len(drifts)

    print_report(all_drifts, args.quiet)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
