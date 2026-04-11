#!/usr/bin/env python3
"""Bazaar text → ConversationExample YAML porter (phase 1.2 PoC).

Reads the five per-layer bazaar text files for one example
conversation and emits a ConversationExample YAML conforming to
schema/kbnet.yaml.

Bazaar text format
------------------

Each example conversation lives in five files under
``/home/sjcarbon/local/src/bazaar/kb.net.shared/`` named
``NN.<title>.<layer>.txt`` where layer is one of ``kansai``,
``standard``, ``english``, ``grammar``, ``word``. Every line is a
single stanza in ``speaker|text`` format. The five files are aligned
row-by-row: row N in every layer is the same stanza, with the same
speaker, expressed in a different layer. The grammar and word layers
use ``(NNN surface_text)`` inline markers to wrap spans that link to
GrammarPoint or Word nodes (NNN is the original Drupal node ID).

PoC scope
---------

This script handles **chapter 1 only**. Generalization to all 12
example conversations and to extracting metadata directly from the
mothball Drupal node HTML is tracked in issue #4. The chapter 1
metadata (title, summary, audio path, character refs, function and
grammar type tags) is hardcoded below; in the full version it will
be parsed from ``_mothball/snapshot/node/264``.

Usage
-----

    python3 tools/import_conversation.py

Writes ``data/conversations/01_with_the_landlord.yaml``. Validate
the output with:

    linkml-validate --schema schema/kbnet.yaml \\
        --target-class ConversationExample \\
        data/conversations/01_with_the_landlord.yaml
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
BAZAAR = Path("/home/sjcarbon/local/src/bazaar/kb.net.shared")
LAYERS = ("kansai", "standard", "english", "grammar", "word")

CHAPTER_1: dict = {
    "id": "conversation_264",
    "drupal_node_id": 264,
    "base": "01.with_the_landlord",
    "title": "大家さんと",
    "title_en": "With the Landlord",
    "summary": (
        "Atsushi leaves his apartment for work in the morning and "
        "meets his landlord cleaning out front."
    ),
    "audio_path": "ex_conv_oya.mp3",
    "characters": [
        "character_214",  # Mori Atsushi
        "character_232",  # The Landlord
    ],
    "function_types": [
        "function_57",   # Question
        "function_111",  # Negation
        "function_118",  # Supplying new information
        "function_119",  # Attentiveness
        "function_120",  # Providing reasons
        "function_121",  # Connecting sentences
        "function_122",  # Honorific titles
        "function_123",  # Soliciting and demonstrating agreement
        "function_126",  # Emphasis
        "function_127",  # Quotation
        "function_128",  # Possession
        "function_131",  # Assertion
        "function_132",  # Nominalization
        "function_137",  # Non-functional
    ],
    "grammar_types": [
        "grammar_19",    # Honorifics
        "grammar_20",    # Obligation
        "grammar_23",    # Conditional
        "grammar_24",    # Giving and receiving
        "grammar_29",    # Imperative
        "grammar_33",    # Progressive
        "grammar_36",    # Completion
        "grammar_38",    # Condition/State
    ],
}


def parse_layer(path: Path) -> list[tuple[str, str]]:
    """Parse a bazaar layer text file into [(speaker, text), ...]."""
    rows: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line:
            continue
        speaker, sep, text = line.partition("|")
        if not sep:
            raise ValueError(
                f"missing '|' separator in {path.name}: {raw!r}"
            )
        rows.append((speaker, text))
    return rows


def build_conversation(meta: dict) -> dict:
    base = meta["base"]
    layer_rows: dict[str, list[tuple[str, str]]] = {
        layer: parse_layer(BAZAAR / f"{base}.{layer}.txt")
        for layer in LAYERS
    }

    n = len(layer_rows["kansai"])
    for layer, rows in layer_rows.items():
        if len(rows) != n:
            raise ValueError(
                f"layer {layer!r} has {len(rows)} stanzas, "
                f"expected {n} (from kansai layer)"
            )
    for i in range(n):
        speakers = {layer: rows[i][0] for layer, rows in layer_rows.items()}
        if len(set(speakers.values())) > 1:
            raise ValueError(
                f"row {i + 1}: speakers differ across layers: {speakers}"
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

    return {
        "id": meta["id"],
        "drupal_node_id": meta["drupal_node_id"],
        "title": meta["title"],
        "title_en": meta["title_en"],
        "summary": meta["summary"],
        "characters": meta["characters"],
        "audio": {"path": meta["audio_path"]},
        "stanzas": stanzas,
        "function_types": meta["function_types"],
        "grammar_types": meta["grammar_types"],
    }


def main() -> None:
    conv = build_conversation(CHAPTER_1)
    out = REPO / "data" / "conversations" / "01_with_the_landlord.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
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
    print(f"wrote {out.relative_to(REPO)} ({len(conv['stanzas'])} stanzas)")


if __name__ == "__main__":
    main()
