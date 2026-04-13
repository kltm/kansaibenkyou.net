# Kansaibenkyou.net

A modern revival of kansaibenkyou.net, a learning resource for Kansai-ben (関西弁) — the family of Japanese dialects spoken in the Kansai region (Osaka, Kyoto, Hyogo, Nara, Wakayama, Shiga). Authored by Keiko Yukawa. Originally a Drupal 7 site, mothballed in 2016 as a static dump on S3 + CloudFront, and being rebuilt here as a Jekyll site (Minimal Mistakes theme) for GitHub Pages.

## The cardinal rule: the old site is the source of truth

The mothballed original at **https://static.kansaibenkyou.net** is the "living memory" of what this site must be. It is a pedagogical tool for dialect self-study where every link, list, table, summary page, text color, and position was chosen through public feedback to create a smooth learning experience.

**When working on this site:**

1. **Never assume the original had nothing.** Before deleting, simplifying, or "fixing" anything, verify against the original site. An incomplete reverse index or missing data mapping is YOUR problem, not evidence that content should not exist.

2. **Never remove functionality to fix a bug.** Removing links to "fix" broken links, or deleting pages because they appear empty in our data, destroys the site's cross-referencing — the core pedagogical mechanism. Fix the data or the rendering instead.

3. **Always check the original before acting.** If direction is unclear, if you're unsure how something "should be", use the living memory. Do not assume. Navigate to the equivalent page on static.kansaibenkyou.net and observe what it does.

4. **Every page serves a purpose.** This is a learning site where users follow thoughts and connections. Taxonomy term pages are glossary definitions AND cross-reference hubs. Index pages are navigation tables with descriptions and tag links. Grammar point pages have structured comparison tables. None of this is decoration.

5. **Verify the full link chain.** After every change, don't just check that your page renders — follow every link you generate and verify the destination has real content. A link to an empty page is worse than no link at all.

6. **Use `tools/` to verify systematically:**
   - `tools/check_links.py` — catches 404s (broken links)
   - `tools/check_empty_pages.py` — catches pages that exist but have no content
   - `tools/verify_site.py` — Playwright-based visual + functional verification
   - Run ALL THREE after every structural change, before committing.

7. **A full sitemap of the old site exists** at `data/old_sitemap.yaml`. The new site must match this topology. For every page in the old sitemap, the new site should have an equivalent page that serves the same purpose.

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
- **Analytics**: GoatCounter (privacy-friendly, no cookies). Snippet in layout, activated when `goatcounter_site` is set in `_config.yml`.

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

### Bazaar dumps (read-only reference)

- `/home/sjcarbon/local/src/bazaar/home/trunk/kansaibenkyou/` — the original Drupal 7 source tree
- `/home/sjcarbon/local/src/bazaar/kb.net.shared/` — per-chapter lesson text files

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

## Lessons learned (from initial rebuild session)

1. **Data preservation ≠ site parity.** Porting all 405 Drupal nodes to YAML was necessary but not sufficient. The rendering layer (Views, display modes, taxonomy cross-references) is equally important.

2. **Drupal's taxonomy system is a cross-referencing engine.** Every taxonomy term page is both a glossary entry AND an aggregation view. The reverse index must cover ALL reference types, not just the ones we happened to import first.

3. **HTML tables in grammar points are pedagogically critical.** The Kansai vs Standard comparison tables, formation rules, and example sentences MUST preserve their tabular structure. Stripping to plain text destroys the learning utility.

4. **baseurl requires discipline.** With the site at `/kansaibenkyou.net/` on github.io, every link in every context (templates, JS, YAML body content) must use `relative_url` or equivalent. This includes JS-generated links (skit.js, banner-carousel.js).

5. **Jekyll collection permalink collisions are silent.** If a `_pages/` stub and a standalone `.html` file both claim the same permalink, Jekyll picks one silently. Always check for collisions after adding new pages.

6. **The original site's design choices were intentional.** Colors (standard=blue, English=green, grammar=purple, words=brown), the green content box (#eaf9f2), the mutual exclusion of grammar/word toggles — all tested through user feedback. Match them, don't "improve" them.
