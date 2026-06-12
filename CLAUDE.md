# Kansaibenkyou.net

A modern revival of kansaibenkyou.net, a learning resource for Kansai-ben (関西弁) — the family of Japanese dialects spoken in the Kansai region (Osaka, Kyoto, Hyogo, Nara, Wakayama, Shiga). Authored by Keiko Yukawa. Originally a Drupal 7 site, mothballed in 2016 as a static dump on S3 + CloudFront, and being rebuilt here as a Jekyll site (Minimal Mistakes theme) for GitHub Pages.

## The cardinal rule: the old site is the source of truth

The mothballed original at **https://static.kansaibenkyou.net** (mirrored locally under `_mothball/`) is the "living memory" of what this site must be. It is a pedagogical tool for dialect self-study where every link, list, table, summary page, text color, position — **and the text content of every field** — was chosen through public feedback to create a smooth learning experience.

**There have been no post-publication human edits.** The 2016 mothball captured the final state of Keiko's edits in Drupal. Any divergence between the mothball and current `data/**/*.yaml` is therefore a regression — either an importer artifact or an earlier "cleanup" mistake — and should be reverted toward the mothball. This applies to:

- Structural elements (links, tables, headings, image classes, audio widgets, speaker labels, field presence)
- **Text content too** — every kana/kanji/romaji character of every published field. The mothball is not just a structural reference; it is the authoritative text. Do NOT normalize `そや`/`せや`, `シャケ`/`サケ`, `かんじょう`/`おあいそ` or similar dialect renderings toward anything other than the mothball.

**When working on this site:**

1. **Never assume the original had nothing.** Before deleting, simplifying, or "fixing" anything, verify against the original site. An incomplete reverse index or missing data mapping is YOUR problem, not evidence that content should not exist.

2. **Never remove functionality to fix a bug.** Removing links to "fix" broken links, or deleting pages because they appear empty in our data, destroys the site's cross-referencing — the core pedagogical mechanism. Fix the data or the rendering instead.

3. **Always check the original before acting.** If direction is unclear, if you're unsure how something "should be", use the living memory. Do not assume. Navigate to the equivalent page on static.kansaibenkyou.net and observe what it does.

4. **Every page serves a purpose.** This is a learning site where users follow thoughts and connections. Taxonomy term pages are glossary definitions AND cross-reference hubs. Index pages are navigation tables with descriptions and tag links. Grammar point pages have structured comparison tables. None of this is decoration.

5. **Verify the full link chain.** After every change, don't just check that your page renders — follow every link you generate and verify the destination has real content. A link to an empty page is worse than no link at all.

6. **Use `tools/` to verify systematically:**
   - `tools/check_links.py` — catches 404s (broken links)
   - `tools/check_empty_pages.py` — catches pages that exist but have no content
   - `tools/check_source_fidelity.py` — counts pedagogical constructs (links, lexicon-indicators, audio widgets, headings, definition lists, etc.) in the mothball HTML and flags any decrease in the YAML
   - `tools/check_text_drift.py` — verbatim text comparison of every imported field against the mothball; exit 1 on any divergence beyond whitespace / HTML-entity normalization
   - `tools/check_taxonomy_coverage.py` — internal taxonomy consistency
   - `tools/verify_site.py` — Playwright-based visual + functional verification
   - `tools/visual_ab.py` — paired old-vs-new screenshots for human visual review
   - Run the data-level checks after every change. Run the visual ones when layout / CSS shifts.

7. **A full sitemap of the old site exists** at `data/old_sitemap.yaml`. The new site must match this topology. For every page in the old sitemap, the new site should have an equivalent page that serves the same purpose. (Caveat: `data/old_sitemap.yaml` reports `has_tagged_content: True` on 25 "Page not found" 404-template terms — confirmed Drupal cruft, leave deleted.)

### Policy amendment (2026-06-11): mutating fixes for provably bad content

Keiko has green-lit fixing **provably bad or malicious** data directly in the YAML — dead hosts, hijacked/squatted domains, and the like. The bar is "provably bad", not "could be improved": text content, dialect renderings, and pedagogy still follow the mothball verbatim. When applying such a fix, record provenance (original URL, replacement, reason) in `data/link_rot.yaml` and add the affected file to the documented-divergences list below so drift triage doesn't revert it.

### Known intentional divergences from mothball

`tools/check_text_drift.py` will always report these — they are not regressions:

- **`data/words/word_112.yaml` and `data/words/word_148.yaml`** commentary fields: mothball uses `http://kansaibenkyou.net/node112` (old-domain absolute URL). New site uses `/words/112/` and `/words/148/` so cross-references actually resolve.
- **`data/pages/page_357.yaml`** body: mothball ended with a static `<table>` of all 12 conversations. New site renders that list dynamically from `site.data.conversations` in `conversations-index.html`, so the YAML keeps only the three intro paragraphs + the kb-dinner image.
- **`data/pages/page_3.yaml`** body (`/resources/`): 7 external URLs (11 anchors) whose hosts died or were hijacked after 2016 now point at a relocated official page (NINJAL) or verified web.archive.org snapshots, each tagged `class="kb-linkrot" data-kb-note="..."` (CSS renders the note as a visible " [note]" suffix). Full provenance in `data/link_rot.yaml`.
- **`data/pages/page_398.yaml`** body (`/development/`): same treatment for `wpaudioplayer.com` (×2 — domain squatted) and `www.zoomh2.net` (dead). Provenance in `data/link_rot.yaml`.

## Status

Rebuild in progress. Live at https://kltm.github.io/kansaibenkyou.net/ (temporary GH Pages URL; will move to kansaibenkyou.net when DNS is configured). Using Minimal Mistakes theme framework.

The mothballed reference still serves at https://static.kansaibenkyou.net.

## License & attribution

This repository is **dual-licensed**:

- **Site content** — lessons, audio, images, text, translations, grammar / vocabulary annotations, conversation scripts, and anything else derived from the original kansaibenkyou.net site — is licensed under **CC BY-SA 3.0**, © Keiko Yukawa. Keiko intends to upgrade this to **CC BY 4.0** *after* the static migration is complete — not before. Preserve the existing license and attribution everywhere it appears in the original content.
- **Site code** — Jekyll layouts and includes, build tools, importers, schemas, JavaScript, CSS, and any other software written for this repository — is licensed under the **BSD 3-Clause License**, © kltm.

## Architecture decisions

- **Theme framework**: Minimal Mistakes (via `remote_theme`). Provides grid, sidebar, masthead, breadcrumbs, responsive layout, and typography. Our custom styling lives in `assets/css/custom.css`, loaded after MM's Sass pipeline.
- **Data model**: LinkML schemas in `schema/`, with canonical content authored as YAML in `data/` and validated at build time via `linkml-validate`.
- **Audio hosting**: in-repo under `assets/audio/` (~87 MiB total).
- **Mothball archive**: `_mothball/` subdirectory, **gitignored — never committed**. 1:1 mirror of the live S3 mothball for offline reference.
- **Search**: Pagefind (static client-side search, indexed in CI via `npx pagefind --site _site`). Search UI at `/search/`.
- **Analytics**: Google Analytics 4 via Minimal Mistakes' built-in `google-gtag` provider (`analytics:` block in `_config.yml`). Measurement ID `G-38LKKSF2EE` — the same property the mothball front page at static.kansaibenkyou.net reports to, kept for stat continuity across the migration. MM emits the snippet only when `JEKYLL_ENV=production` (set by `actions/jekyll-build-pages` in CI), so local builds are analytics-free. History: an earlier GoatCounter integration (chosen 2026-04, snippet lost in the MM theme migration, account never registered) was abandoned 2026-06-11 in favor of GA4 — sjcarbon was uncomfortable loading JS from a single-maintainer remote.

## The data model

Eight Drupal content types, plus taxonomy terms:

| Type | Count | Key fields |
|---|---|---|
| `page` | 12 | body (with headings + images preserved as Markdown) |
| `conversation_example` | 12 | description, characters, audio, stanzas (5 layers), function_types, grammar_types |
| `grammar_point` | 45 | body, commentary, example, formation, formation_from_standard, kansai_vs_standard (**all preserved as HTML with tables**) |
| `real_conversation` | 36 | audio, description, hint, speakers |
| `word` | 280 | body, commentary, standard_kana, standard_kanji, word_types |
| `phonology_topic` | 16 | body |
| `blog` | 4 | body |
| `taxonomy_term` | 207 | label + description (glossary definition) + reverse index (tagged content) |

### The conversation skit toggle widget

Matching the original `kb.js` behavior exactly:

- **Standard/English**: independent toggles, button text changes "Show" ↔ "Hide"
- **Grammar/Words**: mutually exclusive — clicking one hides the other AND hides bare Kansai (skit-k). Both replace skit-k, not stack on top.
- **Colors**: standard=blue, English=green, grammar/word text=grey, grammar links=purple bold (.conv-link-emph-one), word links=brown bold (.conv-link-emph-two)
- **Animation**: CSS max-height/opacity transition (~250ms) matching jQuery `.show('fast')`

### Taxonomy cross-referencing

The taxonomy system serves TWO purposes:
1. **Glossary definitions** — 72 terms have lexicon definitions (e.g., "stem" = "The long (masu) verb form without the final 'masu'"). Stored in `data/taxonomy_descriptions.yaml`.
2. **Content aggregation** — each term page lists all content tagged with that term (grammar points, conversations, real conversations, words). Computed as a reverse index in `data/taxonomy_index.yaml`.

The reverse index must cover ALL reference types: function_types, grammar_types, characters (from conversations), speakers (from real conversations), and word_types.

## Original sources

### Bazaar dumps — historical reference only, NOT a source

- `/home/sjcarbon/local/src/bazaar/home/trunk/kansaibenkyou/` — the original Drupal 7 source tree
- `/home/sjcarbon/local/src/bazaar/kb.net.shared/` — per-chapter lesson text files

⚠️ **These files stop in September 2011.** Keiko continued editing in Drupal for five more years; everything after that lives only in the 2016 mothball at static.kansaibenkyou.net. The bazaar files are pre-publication working drafts and are *obsolete* for any text-content question. An earlier version of `tools/import_conversation.py` read from `kb.net.shared/*.txt` and produced 55 line-level drifts vs the mothball (シャケ→サケ, そや→せや, かんじょう→おあいそ, etc.) — all reverted in commit `70d1fcc`. **Never re-introduce bazaar as a content source.** Use only `_mothball/snapshot/node/<id>` for canonical text.

### S3 buckets

Use the `kbnet-readonly` AWS profile. **Never inline-export the keys.**

| Bucket | Size | Role |
|---|---|---|
| `kb-snapshot` | 172 MiB / 1789 obj | Mothballed Drupal page dump |
| `kb-audio` | 86 MiB / 201 obj | Lesson audio |
| `kb-image` | 55 MiB / 610 obj | Images + banner carousel pool |
| `kb-mobile` | 1 MiB / 42 obj | Old mobile deck (redundant with wrenshoe) |

## Dialect and content handling

- This site teaches **Kansai-ben**, not standard Japanese. Always preserve the distinction.
- Grammar and vocabulary annotations come from the original author and should be treated as **authoritative**. Do not "correct" or paraphrase.
- BCP 47 tags: `ja-x-kansai` for Kansai-ben, `ja` for standard Japanese, `en` for English.

## Security: never commit secrets

- Use the `kbnet-readonly` AWS profile — never inline-export keys.
- Stage files explicitly by name (`git add path/to/file`), never `git add -A`.
- Keep `_mothball/`, `*.pem`, `.env*` in `.gitignore`.

## Lessons learned

### The source of truth principle

The most important lesson: **the old site is the living memory**. Every shortcut taken without verifying against the original caused rework. Specific failures:

- Deleted 58 taxonomy term pages because the reverse index showed them as empty. Every single one had content on the original site (glossary definitions). The reverse index being incomplete was our data gap, not evidence to delete.
- Removed cross-reference links to "fix" broken link checker results. This destroyed the core pedagogical feature — users navigate by following connections between grammar, vocabulary, and conversations.
- Claimed pages were "at parity" after checking they rendered, without clicking the links. Character taxonomy pages (Mori Atsushi, etc.) were empty shells for multiple commits.

**Pattern**: before removing, simplifying, or changing ANYTHING, navigate to the equivalent page on static.kansaibenkyou.net and observe what it does.

### Data import pitfalls

1. **HTML stripping destroys structure.** The initial importer stripped all HTML to plain text, losing tables, headings, image classes, and inline formatting. Grammar point comparison tables, page section headings (h2/h3), and image float classes (`left-image`/`right-image`) all required separate re-import passes with structure preservation. Import with the MOST structure first, then simplify if needed — not the other way around.

2. **Drupal has multiple ID namespaces.** Node IDs and taxonomy term IDs are separate sequences. Term 19 (Honorifics) ≠ node 19. The conversation tag clouds reference taxonomy term IDs but were initially linked to grammar_point node URLs — completely wrong targets. Always be explicit about which ID namespace a reference belongs to.

3. **Field discovery requires scanning, not assuming.** The `field-word-suitability` field (usage icons) was missed during initial word import because it wasn't in the initial field enumeration. The only reliable way to know all fields is to scan the actual HTML for `field-name-*` classes across multiple sample nodes.

### baseurl is a pervasive concern

With the site at `/kansaibenkyou.net/` on github.io, EVERY path reference needs the prefix. This affected:

- Liquid templates: use `| relative_url` on every `href` and `src`
- JavaScript: read baseurl from `<meta name="baseurl">` and prepend to all generated URLs (skit.js link rendering, banner carousel manifest fetch)
- YAML body content: Markdown links `](/path)` need Liquid replacement in the layout; raw HTML `src="/path"` needs separate replacement
- Jekyll frontmatter: `header.overlay_image` paths

**Pattern**: after every change, grep the built HTML for paths missing the prefix. When the custom domain is configured, `baseurl` becomes `""` and all replacements become no-ops.

### Render-side rewrites > YAML modification

Per the cardinal rule, YAML must match the mothball verbatim. Any transformation that arises from the difference between Drupal-2016 and GitHub-Pages-now belongs at the rendering layer, not in the data. Examples already in place:

- **baseurl prefixing** of `href="/..."` and `src="/..."` — Liquid `replace` chain in each content-type layout (`_layouts/page_content.html`, `grammar_point.html`, `word.html`, `real_conversation.html`, `phonology_topic.html`).
- **`http://` → `https://`** on third-party embeds (YouTube on `/intro/`) — same Liquid `replace` chain. Modern browsers block mixed content; original was HTTP because the 2016 site ran over HTTP.
- **`<p class="kb-audio"><a href="...mp3">[↓]</a></p>` → `<audio controls>`** — DOM rewrite in `assets/js/kb-audio.js`, loaded site-wide via `_includes/head/custom.html`. Replaces the Flash-era audio stubs with native HTML5 controls. YAML keeps the mothball markup verbatim.
- **page_357 intro extraction** — `conversations-index.html` renders `site.data.pages.page_357.body` (intro paragraphs + image only; the static table that followed in the mothball is rendered dynamically from `site.data.conversations`).
- **Exception — link rot is fixed in the data, not at render time.** Under the 2026-06-11 mutating-fixes policy, dead/hijacked external URLs are rewritten directly in the page YAML (tagged `kb-linkrot` + `data-kb-note`; CSS `a.kb-linkrot::after` renders the visible " [note]" suffix). `data/link_rot.yaml` is the provenance record, not an active rewrite map. Render-side rewriting remains the rule for everything that is *not* provably bad (baseurl, https upgrades, audio widgets).

**When in doubt**: keep the YAML matching the mothball; apply the transformation in the layout, an include, a Liquid filter, or a small render-side JS. Never re-encode the difference into the data.

### Page layout patterns

- **Data-backed pages** (anything with a corresponding `data/**/*.yaml`): use `layout: page_content` (or the content-type-specific layout like `word`, `grammar_point`, `real_conversation`). These layouts emit `<article class="page-content">` / `<article class="word-entry">` / etc., and CSS in `assets/css/custom.css` gives those a green content box automatically.
- **Index / non-data pages** (feedback, search, vocabulary index, grammar-points index, common-use-list, example-conversations index, real-conversations index): use `layout: single` and wrap the body in `<div class="content-box">`. The `.content-box` CSS rule provides the same green box look.
- **The taxonomy_term layout** emits `<article class="taxonomy-term">`, which is included in the box-rule selector group so every term page gets the box automatically.

If a new page is missing the box, check which of the three patterns above it should be following.

### Jekyll/MM integration patterns

1. **`_layouts/default.html` overrides the ENTIRE theme.** When we switched to Minimal Mistakes, our old `default.html` completely replaced MM's layout — breaking the masthead, sidebar, responsive JS, and everything else. Delete custom `default.html` to let the theme work.

2. **Collection permalink collisions are silent.** A `_pages/357.md` stub and a standalone `conversations-index.html` both claiming `/example-conversations/` — Jekyll picks one with no warning. After adding any page, check for collisions.

3. **MM's blogisms must be explicitly suppressed.** Previous/Next pagination, "Updated" dates, author sidebar boxes — all designed for blogs. Override via empty `_includes/post_pagination.html` and `_includes/page__date.html`. Set `show_date: false` and `classes: wide` in config defaults.

4. **`redirect_to` frontmatter requires a plugin.** Without `jekyll-redirect-from` (not on GH Pages allowlist), use HTML meta refresh redirects instead.

5. **MM's `include_cached` can serve stale content.** If overrides aren't taking effect, the theme may be caching an earlier version of an include.

### CSS specificity with theme frameworks

1. **Custom CSS must use `!important` selectively** to override MM's compiled Sass. The custom skin SCSS (`_sass/minimal-mistakes/skins/_kansaiben.scss`) handles variables; `assets/css/custom.css` handles overrides.

2. **Green content box nesting.** If CSS targets both an `<article>` wrapper AND a nested `<section>`, you get double-boxing. Target only the outermost element per layout. Verify with Playwright: count elements with `backgroundColor === 'rgb(234, 249, 242)'`.

3. **Extract actual colors from the original via Playwright** `getComputedStyle()`, don't guess from screenshots. The original's colors were different from what they appeared (lavender #E3E7F5 not cream, near-black #181818 footer not blue).

### Verification workflow

Run these after EVERY structural change, before committing:

```sh
# Build the site (RUBYOPT= prefix needed on sjcarbon's box — the
# shell sets RUBYOPT=rubygems which Ruby mis-parses)
RUBYOPT= bundle exec jekyll build --quiet

# 1. Broken links
python3 tools/check_links.py

# 2. Empty destination pages
python3 tools/check_empty_pages.py

# 3. Structural fidelity vs mothball (counts tags / features)
python3 tools/check_source_fidelity.py

# 4. Text-level fidelity vs mothball (every character of every field)
python3 tools/check_text_drift.py

# 5. Taxonomy reverse-index consistency
python3 tools/check_taxonomy_coverage.py

# 6. Visual verification (if layout changed)
python3 tools/verify_site.py
# or: python3 tools/visual_ab.py  # paired old/new screenshots

# 7. Schema validation
linkml-validate --schema schema/kbnet.yaml --target-class Word data/words/*.yaml
```

Expected baseline as of 2026-06-11: 0 broken links across ~24,500 refs, 0 layout-empty pages, 0 source-fidelity regressions, 0 text-drift beyond the five documented intentional divergences (words 112/148, page_357, and the link-rot fixes in pages 3/398 — see cardinal-rule section), 23 label-only taxonomy backlog terms (same state as the old site — never-filled slots, leave as-is).

Also: **follow the links you generate**. Click through from a listing page to the destination and verify it has real content. A link to an empty page is worse than no link.

### 2026-04-14 three-agent audit — disposition

A coordinated audit ran three codex agents in parallel (parity, self-audit, cohesion). Reports at `.audit-2026-04-14/` (gitignored). Findings have been triaged; do not re-investigate the following:

- **"25 missing taxonomy term pages"** — all 25 are Drupal 404 cruft (`Page not found` template). Leave deleted. `data/old_sitemap.yaml` reports `has_tagged_content: True` on these as a false positive — do not trust that field.
- **"Missing reverse-index links to grammar_327 from term 24, words 124/125/252 from terms 28/96"** — verified incorrect against mothball. The actual taxonomy refs are `function_37`+`grammar_105` for grammar_327, and `wordtype_18` for words 124/125/252. The current `data/taxonomy_index.yaml` matches the mothball.
- **"23 backlog taxonomy terms need glossary definitions"** — all 23 were also empty on the old site (no description, no tagged content). They are never-filled slots, not lost content. Parity is already met.
- **"Script fidelity drift in example conversations"** — root cause was `tools/import_conversation.py` reading from 2011 bazaar drafts instead of mothball. Fixed in commit `70d1fcc` by switching to mothball as source; 55 drifts → 0.
- **"06-at-karaoke speaker swap"** — real regression (5-stanza 木村/坂上 swap that broke internal callback logic). Fixed in commit `587cb66`, then naturally preserved when the importer was rewritten.

All Tier 1 audit items closed across commits `850e4fd..29027d3`. Remaining deferred items (per sjcarbon, not bugs): no news/feed block restoration, no blog content restoration, no in-site feedback webform (feedback page is a GitHub Issues link).

### URL consistency

All collection URLs use hyphens, no underscores, no `-list` suffix:
- `/example-conversations/:name/`
- `/real-conversations/:name/`
- `/grammar-points/:name/`
- `/words/:name/`
- `/phonology/:name/`
- `/taxonomy/term/:name/`

Update ALL references when changing a URL: config, navigation, layouts, includes, JS, page body content, and the importer's NODE_URL_MAP.
