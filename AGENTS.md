# AGENTS.md — kansaibenkyou.net

This file is loaded into every Codex session that runs in this repo.
It is the project-level brain: cardinal rules, build commands,
verification rituals, and the prompt shape this project expects from a
goal-shaped handoff. CLAUDE.md is the longer narrative; this file is
the operational distillation.

## What this project is

A modern revival of kansaibenkyou.net (a Kansai-ben learning resource
authored by Keiko Yukawa). Originally Drupal 7, mothballed in 2016 as
a static dump on S3 + CloudFront, being rebuilt as a Jekyll site
(Minimal Mistakes theme) for GitHub Pages. The mothballed reference
still serves at https://static.kansaibenkyou.net.

The new site goes live at https://kansaibenkyou.net/ (custom domain
via the repo CNAME file; baseurl is now ""). The old temporary
kltm.github.io/kansaibenkyou.net/ URL no longer renders correctly,
since baseurl="" requires serving from a domain root.

## Cardinal rule: the old site is the source of truth

The mothballed original at **https://static.kansaibenkyou.net** (with
a local mirror under `_mothball/` — gitignored) is the living memory
of what this site must be. Every link, list, table, summary page, and
position was chosen through public feedback to create a smooth
self-study experience.

Three derived rules that must not be violated:

1. **Never assume the original had nothing.** Verify against the
   original site before deleting, simplifying, or "fixing" anything.
2. **Never remove functionality to fix a bug.** Removing a link to
   "fix" a broken link destroys the cross-referencing that is the
   site's core pedagogical mechanism. Fix the data or the rendering.
3. **No parity claim without a comparison artifact.** "It renders" is
   not parity. A claim that page X on the new site matches page X on
   the old site requires (a) the URL on `static.kansaibenkyou.net`,
   (b) the URL or path on the new site, and (c) a specific list of
   what was checked.

This is the rule that has been violated most often. Treat it as
non-negotiable.

### What "parity with the mothball" means in full

The mothball is authoritative for **everything** that was published —
not just structure (field presence, cross-reference links, table
captions, speaker labels) but also the actual text content of every
field. The 2016 site was Keiko's published work, vetted with public
feedback, and frozen in that state. **There have been no
post-publication human edits to the text content** — sjcarbon
confirmed this explicitly. So any divergence between current YAML in
`data/` and the corresponding mothball HTML is a regression with
exactly one of two origins:

1. **Importer artifact** — the BS4 parse or some normalization step
   in `tools/import_content.py` mangled or transformed the text.
2. **Earlier "cleanup" mistake** — some prior pass (script, tool, or
   well-meaning hand-edit) substituted text that didn't need to change.

Both are bugs. Both should be reverted to match the mothball. This
applies to `そや` vs `せや`, `シャケ` vs `サケ`,
`かんじょう` vs `おあいそ`, hiragana ↔ kanji choices, punctuation,
and every other text-level difference. Kansai-ben is regional spoken
Japanese — there are many valid renderings — but the site's job is to
present *Keiko's recorded, published version* of it, not to "improve"
it. The mothball is what was recorded and published; the YAML must
match.

(Caveat for backlog: a taxonomy term that had no content on the old
site is at parity when it has no content on the new site. Don't
generate fill-in work for slots that were already empty.)

## How to take a goal-shaped task

When the user (or another agent) hands off a task, expect these four
ingredients and refuse to start without them:

1. **One named objective** — the verifiable thing to be true at the end.
2. **A stopping condition** — a command, grep, count, or comparison
   that can be re-run, that flips from false to true when the goal is met.
3. **File pointers** — the specific paths to inspect and modify, plus
   the corresponding mothball reference if applicable.
4. **Validation commands** — the shell commands to run to prove the
   stopping condition holds. These must be runnable from this repo.

If the handoff is missing one of these, ask for it before starting.
A goal that says "improve the X page" without a stopping condition
will produce drift, not progress.

## Build and verification commands

```sh
# Build the site (RUBYOPT must be cleared — local shell sets
# RUBYOPT=rubygems which Ruby mis-parses as -rubygems → -r ubygems)
RUBYOPT= bundle exec jekyll build --quiet

# Verification suite — run all three after every structural change
python3 tools/check_links.py              # broken links across _site
python3 tools/check_empty_pages.py        # pages that exist but render empty
python3 tools/check_source_fidelity.py    # mothball HTML feature counts vs YAML
python3 tools/check_taxonomy_coverage.py  # taxonomy reverse-index consistency

# Visual A/B (paired old vs new screenshots, side-by-side index)
# Requires Playwright + a local server on 127.0.0.1:4000
python3 tools/visual_ab.py

# Schema validation
linkml-validate --schema schema/kbnet.yaml --target-class Word data/words/*.yaml
```

The verification suite is non-optional for any structural change. A
clean baseline at the time this file was written:

* 0 broken links (24,466 refs across 2,755 served paths)
* 0 layout-empty pages
* 0 source-fidelity regressions (every link, lexicon-indicator,
  audio widget, table caption, heading, and definition-list entry
  preserved through import)
* 23 backlog taxonomy terms (label-only — Tier 2 work, tracked)

If a change makes any of those numbers worse, that is a regression.

## Project layout (the parts you'll touch most)

```
data/
  words/word_<id>.yaml              280 entries
  grammar_points/grammar_<id>.yaml  45 entries
  real_conversations/<id>.yaml      36 entries
  example_conversations/<id>.yaml   12 entries (audio skits)
  phonology_topics/<id>.yaml        16 entries
  pages/page_<id>.yaml              12 entries
  taxonomy_descriptions.yaml        glossary definitions
  taxonomy_index.yaml               reverse index (terms → tagged content)
  taxonomy_labels.yaml              term-id → human label

schema/kbnet.yaml                   LinkML schema for the data model

_layouts/                           per-content-type templates
_includes/                          shared partials
assets/css/custom.css               overrides MM theme

tools/                              importer + verification scripts
  import_content.py                 the importer (BS4-based)
  check_*.py                        the verification suite
  visual_ab.py                      paired screenshots

_mothball/                          local mirror of static.kansaibenkyou.net
                                    (gitignored — never committed)
```

URLs: hyphenated, no underscores, no `-list` suffix
(`/grammar-points/<slug>/`, `/words/<slug>/`,
`/taxonomy/term/<id>/`, etc.).

## Failure modes that have actually happened

These are the recurring bugs. Watch for them in your own output.

* **HTML stripping during import** — losing tables, headings, image
  classes, lexicon-indicators, anchors. Fix in the importer, then
  re-run; do not patch individual YAML files by hand.
* **Drupal ID-namespace confusion** — node IDs ≠ taxonomy term IDs.
  Tag clouds reference taxonomy term IDs, not node URLs. Always be
  explicit about which namespace.
* **baseurl mismatches** — the site lives at /kansaibenkyou.net/ on
  GH Pages. Every absolute path in templates needs `| relative_url`;
  every absolute href/src in imported HTML needs the per-layout
  baseurl rewrite (see `_layouts/grammar_point.html` for the pattern).
* **Permalink collisions** — Jekyll picks one silently. After adding
  a page, grep `_site/` for the permalink to confirm only one source
  produced it.
* **MM theme cache** — `include_cached` can serve stale partials. If
  an override doesn't take, suspect this.
* **CSS specificity vs MM Sass** — `assets/css/custom.css` overrides
  MM by being loaded after; `!important` is acceptable here. Variables
  belong in `_sass/minimal-mistakes/skins/_kansaiben.scss`.

## Things not to do without the user in the loop

* **Auto-revert script edits.** If the YAML data and the mothball
  HTML diverge (シャケ → サケ etc.), this may be Keiko's deliberate
  edit, not a regression. Flag and ask, do not revert.
* **Bulk-create taxonomy terms from the mothball.** The mothball
  includes term ID 100 literally named "Page not found". Surface
  apparent gaps; do not fill them blindly.
* **Push commits or open PRs.** Commit yes (small, labeled, verified),
  push no, unless explicitly asked.

## Working style this project expects

* **Small, labeled, verified commits.** Each commit should pass the
  verification suite. Commit messages explain *why*, not just *what*.
* **Inspect → plan → execute, for non-trivial work.** Especially for
  refactors, migrations, or bulk YAML edits.
* **Use the verification tools as the source of truth for "done".**
  A goal that doesn't terminate at a tool's output is not goal-shaped.
* **Reuse the thread.** If you're working on a multi-step objective,
  stay in one thread rather than starting fresh per step.

## Status (as of 2026-05-10)

Tier 1 mechanical fixes from the 2026-04-14 audit are landed.
Tier 2 work — content + functional + pedagogical parity with the old
site, with light modernization — is the current focus. Tier 3
(structural cleanup, vocab sort controls, build-time skit anchors)
and DNS cutover are out of scope for this push.
