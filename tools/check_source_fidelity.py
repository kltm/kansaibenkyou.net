#!/usr/bin/env python3
"""Source-to-data fidelity check.

For every Drupal node we import, count the pedagogical constructs
present in the mothball HTML source vs the constructs present in the
corresponding YAML data file. Any decrease is flagged.

The checker is deliberately structural (it counts features, not bytes)
because fidelity losses on this site have repeatedly snuck past byte-
level and correctness-level tooling. Tag-count diff catches:

    * `<a>` links silently stripped from page bodies
    * `<sup class="lexicon-indicator">` glossary pointers stripped
    * `<audio>` / `kb-audio` widget loss
    * `<dl>/<dt>/<dd>` definition-list structure flattened
    * `<table>/<caption>` captions or headers dropped
    * `<h2>/<h3>/<h4>` section hierarchy lost or merged
    * `<img>` with authorial classes (left-image, right-image,
      suitability-img) discarded

Only *losses* are flagged. New elements on the data side (e.g. a link
we added during import to resolve a bare-ID href) are reported as
rewrites, not failures.

Usage:

    python3 tools/check_source_fidelity.py
    python3 tools/check_source_fidelity.py --strict  # exit 1 on any loss
    python3 tools/check_source_fidelity.py --details  # per-node detail
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
MOTHBALL = REPO / "_mothball" / "snapshot" / "node"
DATA = REPO / "data"

# Per content type: the article-class Drupal used to identify the node,
# the data directory, the YAML filename prefix, and the fields we know
# we import from (either as HTML or as text). Field names match the
# Drupal `field-name-{X}` class. `body` is the node body; the rest are
# Drupal "extra fields" attached to the content type.
CONTENT_TYPES = {
    "grammar_points": {
        "article_class": "article-grammar-point",
        "prefix": "grammar",
        "html_fields": [
            "body",
            "field-gp-commentary",
            "field-gp-example",
            "field-gp-formation",
            "field-gp-formation-from-std",
            "field-gp-kansai-v-std",
        ],
        "yaml_html_keys": [
            "body",
            "commentary",
            "example",
            "formation",
            "formation_from_standard",
            "kansai_vs_standard",
        ],
    },
    "words": {
        "article_class": "article-type-word",
        "prefix": "word",
        "html_fields": [
            "body",
            "field-word-commentary",
            "field-word-example",
            "field-word-kanji",
            "field-word-standard",
            "field-word-standard-kanji",
            "field-word-suitability",
        ],
        "yaml_html_keys": [
            "body",
            "commentary",
            "example",
            "kanji",
            "standard_kana",
            "standard_kanji",
            # suitability is a list of dicts, handled separately
        ],
    },
    "phonology_topics": {
        "article_class": "article-phonology-topic",
        "prefix": "phonology",
        "html_fields": ["body"],
        "yaml_html_keys": ["body"],
    },
    "real_conversations": {
        "article_class": "article-real-conversation",
        "prefix": "real_conversation",
        "html_fields": [
            "field-real-conv-desc",
            "field-real-conv-hint",
        ],
        "yaml_html_keys": ["summary", "hint"],
    },
    "pages": {
        "article_class": "article-type-page",
        "prefix": "page",
        "html_fields": ["body"],
        "yaml_html_keys": ["body"],
    },
}

# Feature counter: given a BeautifulSoup subtree, return a dict of counts.
def count_features(subtree) -> dict[str, int]:
    if subtree is None:
        return {}
    # Stringify text inside subtree so we can scan for literal markup
    # that may have survived as text (e.g. `<a>` rendered as `&lt;a&gt;`
    # in a malformed import).
    counts: dict[str, int] = defaultdict(int)
    counts["anchor"] = len(subtree.find_all("a"))
    counts["image"] = len(subtree.find_all("img"))
    counts["audio"] = len(subtree.find_all(["audio", "source"]))
    counts["lexicon_indicator"] = len(
        subtree.find_all("sup", class_="lexicon-indicator")
    )
    counts["dl"] = len(subtree.find_all("dl"))
    counts["dt"] = len(subtree.find_all("dt"))
    counts["dd"] = len(subtree.find_all("dd"))
    counts["table"] = len(subtree.find_all("table"))
    counts["caption"] = len(subtree.find_all("caption"))
    counts["h2"] = len(subtree.find_all("h2"))
    counts["h3"] = len(subtree.find_all("h3"))
    counts["h4"] = len(subtree.find_all("h4"))
    counts["ul"] = len(subtree.find_all("ul"))
    counts["ol"] = len(subtree.find_all("ol"))
    counts["li"] = len(subtree.find_all("li"))
    counts["em"] = len(subtree.find_all("em"))
    counts["strong"] = len(subtree.find_all("strong"))
    # kb-audio widgets (Drupal custom audio block)
    counts["kb_audio_widget"] = len(
        subtree.find_all(class_="kb-audio")
    )
    # Specialised <img> classes — pedagogical wrappers.
    for img in subtree.find_all("img"):
        for cls in img.get("class") or []:
            if cls in {"left-image", "right-image", "suitability-img"}:
                counts[f"img_{cls.replace('-', '_')}"] += 1
    return dict(counts)


# We INTENTIONALLY discard some Drupal-specific constructs during
# import because they are chrome, not content. Subtract these from
# source counts before comparing to data counts.
def strip_chrome(subtree):
    """Remove elements we deliberately don't import."""
    if subtree is None:
        return
    # `<h2 class="field-label">` is Drupal's "Commentary:" / "Example:"
    # field-label, rendered by our layout instead.
    for lbl in subtree.find_all("h2", class_="field-label"):
        lbl.decompose()
    # Drupal's `.field-items` / `.field-item` wrappers.
    for wrapper in subtree.find_all("div", class_=lambda c: c and (
        "field-items" in c or (
            isinstance(c, list) and any(x.startswith("field-item") for x in c)
        )
    )):
        wrapper.unwrap()


# -------- source-side inventory --------

def scan_node_sources(node_id: int, article_class: str, fields: list[str]) -> dict[str, int]:
    """Parse a mothball node file and count features across its fields."""
    path = MOTHBALL / str(node_id)
    if not path.exists():
        return {}
    html = path.read_text(errors="replace")
    if f"article {article_class}" not in html:
        return {}
    soup = BeautifulSoup(html, "lxml")
    totals: dict[str, int] = defaultdict(int)
    for fname in fields:
        field_div = soup.find(class_=f"field-name-{fname}")
        if field_div is None:
            continue
        # Work on a clone so strip_chrome doesn't mutate the shared DOM.
        clone = BeautifulSoup(str(field_div), "lxml")
        strip_chrome(clone)
        c = count_features(clone)
        for k, v in c.items():
            totals[k] += v
    return dict(totals)


# -------- data-side inventory --------

def scan_data_counts(yaml_path: Path, html_keys: list[str],
                     extra_counter=None) -> dict[str, int]:
    """Load a YAML data file and count features across its HTML fields."""
    if not yaml_path.exists():
        return {}
    data = yaml.safe_load(yaml_path.read_text()) or {}
    if not isinstance(data, dict):
        return {}
    totals: dict[str, int] = defaultdict(int)
    combined_html = []
    for key in html_keys:
        v = data.get(key)
        if isinstance(v, str) and v:
            combined_html.append(v)
    if combined_html:
        soup = BeautifulSoup("<div>" + "".join(combined_html) + "</div>",
                             "lxml")
        c = count_features(soup)
        for k, v in c.items():
            totals[k] += v
    if extra_counter is not None:
        for k, v in extra_counter(data).items():
            totals[k] = totals.get(k, 0) + v
    return dict(totals)


def word_extra_counter(data: dict) -> dict[str, int]:
    """Words carry suitability indicators as a list of icon dicts rather
    than HTML. Count each entry as one suitability-img and one anchor-
    equivalent (the icon links back to the glossary on old site)."""
    out: dict[str, int] = defaultdict(int)
    suits = data.get("suitability") or []
    if isinstance(suits, list):
        out["image"] += len(suits)
        out["img_suitability_img"] += len(suits)
    return dict(out)


# -------- diffing --------

def diff(source: dict[str, int], data: dict[str, int]) -> dict[str, dict]:
    """Return {feature: {source, data, delta}} for every feature where
    there is any asymmetry, keyed by feature name."""
    keys = set(source) | set(data)
    out: dict[str, dict] = {}
    for k in sorted(keys):
        s = source.get(k, 0)
        d = data.get(k, 0)
        if s == d:
            continue
        out[k] = {"source": s, "data": d, "delta": d - s}
    return out


# Which features are LOSSES worth failing on (decrease from source
# to data). Some deltas are expected zero; others we tolerate.
# Keys here match the feature name in count_features().
HARD_FAIL_FEATURES = {
    "anchor",
    "lexicon_indicator",
    "image",
    "audio",
    "kb_audio_widget",
    "dl",
    "dt",
    "dd",
    "table",
    "caption",
    "h2",
    "h3",
    "h4",
    "img_left_image",
    "img_right_image",
    "img_suitability_img",
}

# Anchors we deliberately add during import (bare-ID rewrites) can
# LEGITIMATELY increase the anchor count. `em` and `strong` normalisation
# by lxml can legitimately shift counts slightly. Track but don't hard-fail.
SOFT_TRACK_FEATURES = {"em", "strong", "ul", "ol", "li"}


# -------- driver --------

def discover_nodes(article_class: str) -> list[int]:
    out: list[int] = []
    for f in MOTHBALL.iterdir():
        if not f.name.isdigit():
            continue
        try:
            content = f.read_text(errors="replace")
        except Exception:
            continue
        if f"article {article_class}" in content:
            out.append(int(f.name))
    return sorted(out)


def main() -> None:
    strict = "--strict" in sys.argv
    details = "--details" in sys.argv

    total_losses = 0
    per_type_summary: dict[str, dict[str, int]] = {}

    for ctype, spec in CONTENT_TYPES.items():
        node_ids = discover_nodes(spec["article_class"])
        data_dir = DATA / ctype
        print(f"\n=== {ctype}: {len(node_ids)} nodes ===")
        feature_losses: dict[str, int] = defaultdict(int)
        nodes_with_loss: list[tuple[int, dict]] = []
        extra = word_extra_counter if ctype == "words" else None
        for nid in node_ids:
            yaml_path = data_dir / f"{spec['prefix']}_{nid}.yaml"
            source = scan_node_sources(nid, spec["article_class"],
                                       spec["html_fields"])
            dataside = scan_data_counts(yaml_path, spec["yaml_html_keys"],
                                        extra_counter=extra)
            d = diff(source, dataside)
            if not d:
                continue
            node_lost = {
                feat: info for feat, info in d.items()
                if info["delta"] < 0 and feat in HARD_FAIL_FEATURES
            }
            if node_lost:
                nodes_with_loss.append((nid, node_lost))
                for feat, info in node_lost.items():
                    feature_losses[feat] += -info["delta"]
        # Per-type summary
        print(f"  nodes with feature loss: {len(nodes_with_loss)}")
        if feature_losses:
            print("  aggregate losses by feature:")
            for feat, n in sorted(feature_losses.items(),
                                   key=lambda kv: -kv[1]):
                print(f"    -{n:<4} {feat}")
                total_losses += n
        per_type_summary[ctype] = dict(feature_losses)
        if details and nodes_with_loss:
            print("  per-node details (first 20):")
            for nid, node_lost in nodes_with_loss[:20]:
                fragments = [
                    f"{feat}({info['source']}→{info['data']})"
                    for feat, info in sorted(node_lost.items())
                ]
                print(f"    node {nid}: " + ", ".join(fragments))
            if len(nodes_with_loss) > 20:
                print(f"    ... and {len(nodes_with_loss) - 20} more")

    print("\n=== SUMMARY ===")
    for ctype, losses in per_type_summary.items():
        if losses:
            total = sum(losses.values())
            print(f"  {ctype}: -{total} across "
                  f"{len(losses)} feature categor{'y' if len(losses)==1 else 'ies'}")
        else:
            print(f"  {ctype}: OK")
    print(f"\nTotal features lost from source → data: {total_losses}")
    if total_losses > 0 and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
