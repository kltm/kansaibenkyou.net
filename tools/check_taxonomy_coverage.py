#!/usr/bin/env python3
"""Taxonomy coverage check.

Walks all content YAML files and reports where the taxonomy system
is inconsistent:

  1. Terms referenced from content but with no label.
  2. Labels with neither a description nor a reverse-index entry
     (these render as empty pages — the regression that previously
     led to deleting 58 term pages; flagged as a BACKLOG item, not
     a CI failure).
  3. Entries in the reverse index whose term has no label.
  4. Reference types whose aggregation into the index may be missing
     (function_types, grammar_types, characters, speakers, word_types).

Usage:

    python3 tools/check_taxonomy_coverage.py
    python3 tools/check_taxonomy_coverage.py --strict  # fail on inconsistencies
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CONTENT_DIRS = [
    "grammar_points",
    "words",
    "conversations",
    "real_conversations",
    "phonology_topics",
    "pages",
]

# Field names on content records that carry taxonomy references. Each
# entry is a field name whose value is a list of references like
# "function_131" or "grammar_88"; the integer suffix is the term id.
REFERENCE_FIELDS = [
    "function_types",
    "grammar_types",
    "characters",
    "speakers",
    "word_types",
]


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def extract_term_id(ref: str) -> str:
    """'function_131' -> '131'; '131' -> '131'."""
    s = str(ref)
    if "_" in s:
        return s.rsplit("_", 1)[-1]
    return s


def collect_references() -> dict[str, dict[str, list[str]]]:
    """Map term_id -> {source_path: [field_names]}."""
    refs: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for cdir in CONTENT_DIRS:
        d = DATA / cdir
        if not d.exists():
            continue
        for path in sorted(d.glob("*.yaml")):
            data = load_yaml(path)
            if not isinstance(data, dict):
                continue
            rel = str(path.relative_to(REPO))
            for field in REFERENCE_FIELDS:
                vals = data.get(field) or []
                if not isinstance(vals, list):
                    continue
                for v in vals:
                    tid = extract_term_id(v)
                    refs[tid][rel].append(field)
    return refs


def main() -> None:
    strict = "--strict" in sys.argv

    labels = load_yaml(DATA / "taxonomy_labels.yaml")
    descs = load_yaml(DATA / "taxonomy_descriptions.yaml")
    index = load_yaml(DATA / "taxonomy_index.yaml")

    label_ids = {str(k) for k in labels}
    desc_ids = {str(k) for k in descs}
    index_ids = {str(k) for k in index}

    references = collect_references()
    ref_ids = set(references)

    print(
        f"labels={len(label_ids)}  descriptions={len(desc_ids)}  "
        f"index={len(index_ids)}  referenced_by_content={len(ref_ids)}"
    )
    print()

    # 1. Terms referenced from content but with no label.
    referenced_no_label = sorted(ref_ids - label_ids, key=int)
    if referenced_no_label:
        print(f"[FAIL] Terms referenced by content but missing a label: "
              f"{len(referenced_no_label)}")
        for tid in referenced_no_label[:20]:
            sources = list(references[tid])[:3]
            print(f"  {tid}  (referenced by: {', '.join(sources)})")
        if len(referenced_no_label) > 20:
            print(f"  ... and {len(referenced_no_label) - 20} more")
        print()

    # 2. Labels with neither description nor reverse-index entry.
    # A term is considered to have a reverse-index entry when its
    # index[tid] contains at least one non-empty group (grammar_points,
    # conversations, etc.).
    def index_has_entries(tid: str) -> bool:
        entry = index.get(tid)
        if not isinstance(entry, dict):
            return bool(entry)
        return any(entry.values())

    empty_shells = sorted(
        (tid for tid in label_ids
         if tid not in desc_ids and not index_has_entries(tid)),
        key=int,
    )
    if empty_shells:
        print(f"[BACKLOG] Labels with no description and no reverse-index "
              f"entries: {len(empty_shells)}")
        print("          (these render as bare-title pages; not a CI failure,")
        print("          but each is a pedagogical dead end until backfilled)")
        for tid in empty_shells[:20]:
            label = labels.get(tid) or labels.get(int(tid))
            print(f"  {tid}  {label!r}")
        if len(empty_shells) > 20:
            print(f"  ... and {len(empty_shells) - 20} more")
        print()

    # 3. Index entries with no label.
    idx_no_label = sorted(index_ids - label_ids, key=int)
    if idx_no_label:
        print(f"[FAIL] Reverse-index entries with no label: {len(idx_no_label)}")
        for tid in idx_no_label[:20]:
            print(f"  {tid}")
        print()

    # 4. Descriptions with no label.
    desc_no_label = sorted(desc_ids - label_ids, key=int)
    if desc_no_label:
        print(f"[FAIL] Description entries with no label: {len(desc_no_label)}")
        for tid in desc_no_label[:20]:
            print(f"  {tid}")
        print()

    # 5. Terms referenced from content but missing from reverse index.
    # These are the links that WOULD work on the taxonomy page but the
    # hub page won't list them — a broken cross-reference hub.
    referenced_not_in_index = sorted(
        (tid for tid in ref_ids if not index_has_entries(tid)),
        key=int,
    )
    if referenced_not_in_index:
        print(f"[WARN] Terms referenced by content but absent from the "
              f"reverse index: {len(referenced_not_in_index)}")
        print("       (term page won't list the content that references it)")
        for tid in referenced_not_in_index[:20]:
            label = labels.get(tid) or labels.get(int(tid)) or "?"
            sources = list(references[tid])[:2]
            print(f"  {tid}  {label!r}  (<- {', '.join(sources)})")
        if len(referenced_not_in_index) > 20:
            print(f"  ... and {len(referenced_not_in_index) - 20} more")
        print()

    hard_fail = bool(referenced_no_label or idx_no_label or desc_no_label
                     or referenced_not_in_index)
    if hard_fail:
        print("SUMMARY: taxonomy is inconsistent "
              "(see [FAIL]/[WARN] sections above).")
        if strict:
            sys.exit(1)
    else:
        print("SUMMARY: taxonomy coverage is internally consistent.")
        if empty_shells:
            print(f"         ({len(empty_shells)} label-only terms remain as "
                  f"content backlog.)")


if __name__ == "__main__":
    main()
