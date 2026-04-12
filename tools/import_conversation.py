#!/usr/bin/env python3
"""Bazaar text + mothball HTML → ConversationExample YAML porter.

Reads the five per-layer bazaar text files for each example
conversation (kansai/standard/english/grammar/word) and extracts
metadata (title, summary, audio, characters, function and grammar
type tags) from the corresponding mothball Drupal node HTML. Outputs
a ConversationExample YAML conforming to schema/kbnet.yaml.

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

REPO = Path(__file__).resolve().parent.parent
BAZAAR = Path("/home/sjcarbon/local/src/bazaar/kb.net.shared")
MOTHBALL_NODES = REPO / "_mothball" / "snapshot" / "node"
LAYERS = ("kansai", "standard", "english", "grammar", "word")

CHAPTERS: list[tuple[int, int, str]] = [
    (1,  264, "01.with_the_landlord"),
    (2,  265, "02.at_the_welcome_party"),
    (3,  266, "03.at_the_shops"),
    (4,  267, "04.at_the_fish_monger"),
    (5,  268, "05.asking_directions"),
    (6,  269, "06.at_karaoke"),
    (7,  270, "07.on_a_train"),
    (8,  271, "08.with_a_neighbor"),
    (9,  272, "09.at_work"),
    (10, 273, "10.on_a_break"),
    (11, 274, "11.at_a_pub"),
    (12, 275, "12.at_okonomiyaki"),
]


def extract_metadata(node_id: int) -> dict:
    """Parse metadata from a mothball Drupal conversation node HTML."""
    raw = (MOTHBALL_NODES / str(node_id)).read_text(
        encoding="utf-8", errors="replace"
    )

    m = re.search(r"<title>(.+?) \| Kansaibenkyou", raw)
    full_title = html_mod.unescape(m.group(1)) if m else ""
    parts = full_title.split(" / ", 1)
    title_ja = parts[0].strip()
    title_en = parts[1].strip() if len(parts) > 1 else ""

    m = re.search(
        r'field-name-field-conv-exp-desc.*?field-item even">(.*?)\n',
        raw, re.DOTALL,
    )
    desc = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""

    m = re.search(
        r'field-name-field-conv-exp-audio.*?href="[^"]*?/([^/"]+\.mp3)"',
        raw, re.DOTALL,
    )
    audio = m.group(1) if m else ""

    def extract_term_ids(field_name: str) -> list[str]:
        section = re.search(
            rf"field-name-{field_name}(.*?)</section>", raw, re.DOTALL,
        )
        if not section:
            return []
        return re.findall(r"taxonomy/term/(\d+)", section.group(1))

    char_ids = extract_term_ids("field-conv-exp-tags")
    func_ids = extract_term_ids("field-function-type")
    gram_ids = extract_term_ids("field-grammar-type")

    return {
        "title": title_ja,
        "title_en": title_en,
        "summary": desc,
        "audio_path": audio,
        "characters": [f"character_{i}" for i in char_ids],
        "function_types": [f"function_{i}" for i in func_ids],
        "grammar_types": [f"grammar_{i}" for i in gram_ids],
    }


def parse_layer(path: Path) -> list[tuple[str, str]]:
    """Parse a bazaar layer text file into [(speaker, text), ...].

    Lines without a ``|`` separator are treated as stage directions
    (e.g. ``(Drinking begins...)``). These get an empty-string speaker.

    Handles a known data errata in the bazaar files where a ``(NNN``
    annotation marker appears before the ``|`` separator instead of
    after it (e.g. ``のり子(166|ほやけど)`` should be
    ``のり子|(166ほやけど)``).
    """
    rows: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line:
            continue
        speaker, sep, text = line.partition("|")
        if not sep:
            rows.append(("", line))
        else:
            m = re.match(r"^(.+?)(\(\d+)$", speaker)
            if m:
                speaker = m.group(1)
                text = m.group(2) + text
            rows.append((speaker, text))
    return rows


def build_conversation(
    ch_num: int, node_id: int, base: str
) -> tuple[dict, Path]:
    """Build a ConversationExample dict from bazaar text + mothball HTML."""
    meta = extract_metadata(node_id)

    layer_rows: dict[str, list[tuple[str, str]]] = {
        layer: parse_layer(BAZAAR / f"{base}.{layer}.txt")
        for layer in LAYERS
    }

    n = len(layer_rows["kansai"])
    for layer, rows in layer_rows.items():
        if len(rows) != n:
            raise ValueError(
                f"ch{ch_num} layer {layer!r} has {len(rows)} stanzas, "
                f"expected {n} (from kansai layer)"
            )
    for i in range(n):
        speakers = {layer: rows[i][0] for layer, rows in layer_rows.items()}
        if len(set(speakers.values())) > 1:
            raise ValueError(
                f"ch{ch_num} row {i + 1}: speakers differ: {speakers}"
            )

    stanzas: list[dict] = []
    for i in range(n):
        speaker = layer_rows["kansai"][i][0]
        kansai = layer_rows["kansai"][i][1]
        stanza: dict = {
            "speaker": speaker,
            "kansai": kansai,
            "standard": layer_rows["standard"][i][1],
            "english": layer_rows["english"][i][1],
        }
        grammar_text = layer_rows["grammar"][i][1]
        word_text = layer_rows["word"][i][1]
        if grammar_text != kansai:
            stanza["kansai_grammar"] = grammar_text
        if word_text != kansai:
            stanza["kansai_word"] = word_text
        stanzas.append(stanza)

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
