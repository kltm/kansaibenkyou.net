# Kansaibenkyou.net

A modern revival of kansaibenkyou.net, a learning resource for Kansai-ben (関西弁) — the family of Japanese dialects spoken in the Kansai region (Osaka, Kyoto, Hyogo, Nara, Wakayama, Shiga). Authored by Keiko Yukawa. Originally a Drupal 7 site, mothballed in 2016 as a static dump on S3 + CloudFront, and being rebuilt here as a Jekyll site for GitHub Pages under the original `kansaibenkyou.net` domain.

## Status

Greenfield. The mothballed reference still serves at https://static.kansaibenkyou.net (CloudFront in front of S3 bucket `kb-snapshot`). The revived site target is the bare `kansaibenkyou.net` domain on GitHub Pages.

## License & attribution

This repository is **dual-licensed**:

- **Site content** — lessons, audio, images, text, translations, grammar / vocabulary annotations, conversation scripts, and anything else derived from the original kansaibenkyou.net site — is licensed under **CC BY-SA 3.0**, © Keiko Yukawa. Keiko intends to upgrade this to **CC BY 4.0** *after* the static migration is complete — not before. Preserve the existing license and attribution everywhere it appears in the original content.
- **Site code** — Jekyll layouts and includes, build tools, importers, schemas, JavaScript, CSS, and any other software written for this repository — is licensed under the **BSD 3-Clause License**, © kltm.

Rule of thumb: anything under `data/`, `assets/audio/`, `assets/banner/`, `assets/images/`, or `_data/` is **content**. Anything under `_layouts/`, `_includes/`, `assets/css/`, `assets/js/`, `schema/`, or `tools/` is **code**. See `LICENSE` for the full text of both.

## Architecture decisions

- **Static site generator**: Jekyll. Native to GitHub Pages, zero build-action path, well-known to the maintainer. Astro was considered and rejected: its only meaningful win for this project (islands hydration for the conversation widget) is replaceable with ~30 lines of vanilla JS.
- **Data model**: LinkML schemas in `schema/`, with canonical content authored as YAML in `data/` and validated at build time via `linkml-validate`. Schema patterns mirror the sister project `wrenshoe`.
- **Audio hosting**: in-repo under `assets/audio/` (~86 MiB total). Revisit only if GitHub Pages bandwidth becomes a real problem.
- **Mothball archive**: a `_mothball/` subdirectory of this repo holds a 1:1 mirror of the live S3 mothball for offline reference. **Gitignored — never committed**, excluded from the Jekyll build.
- **Subdomain split**: `wrenshoe.kansaibenkyou.net` will mount the wrenshoe app's kansaiben deck (replacing the original `mobile.kansaibenkyou.net`).
- **Analytics**: privacy-friendly (Plausible / GoatCounter / similar). No Google Analytics — the original GA was stripped during the 2016 mothballing and is not coming back.

## Repository layout

```
.
├── CLAUDE.md            # this file
├── LICENSE              # CC BY-SA 3.0
├── README.md
├── _config.yml          # Jekyll config
├── Gemfile              # Jekyll gems
├── _layouts/            # Jekyll templates
├── _data/               # Jekyll data files (rendered from data/*.yaml)
├── assets/
│   ├── audio/           # lesson mp3s (mirrored from kb-audio)
│   ├── banner/          # header carousel images (from kb-image/banner/)
│   └── images/          # chapter images (from kb-image/)
├── data/                # canonical YAML content (LinkML-validated)
│   ├── conversations/
│   ├── real_conversations/
│   ├── grammar_points/
│   ├── words/
│   ├── phonology_topics/
│   ├── pages/
│   └── characters/
├── schema/              # LinkML schemas
│   └── kbnet.yaml
├── tools/               # one-shot scripts, importers, validators
└── _mothball/           # GITIGNORED — local mirror of the four S3 buckets
```

## The data model — ground truth from the Drupal 7 dump

Eight Drupal content types, enumerated by scanning `<article class>` across all 406 nodes in the mothball:

| Type | Count | Fields beyond `body` |
|---|---|---|
| `page` | 12 | (body only) |
| `conversation_example` | 12 | description, characters, audio, function types, grammar types |
| `grammar_point` | 45 | commentary, example, formation, formation-from-standard, kansai-vs-standard, function type, grammar type |
| `real_conversation` | 36 | audio, description, hint, tags (speakers) |
| `word` | 280 | commentary, standard (kana), standard kanji, word type |
| `phonology_topic` | 16 | (body only) |
| `blog` | 4 | (body only) |
| `webform` | 1 | the original feedback form — drop, replace with a GitHub Issues link or external form service |

**The 12 example conversations** are nodes 264–275, lining up exactly with the bazaar `kb.net.shared/01.with_the_landlord.*` through `12.at_an_okonomiyaki_restaurant.*` text files and the `kb-audio/ex_conv_*.mp3` files.

**Real conversations** landing page is node 387.

**Characters are taxonomy terms** (terms 214–232 in the original Drupal taxonomy), separate from grammar / function-type taxonomy terms (~111–137).

### The "Example conversation" interactive widget

This was the original site's most JS-heavy feature, but it's structurally simple. Each stanza is a `<ul>` of five layered `<li>` elements with class names, plus four toggle buttons:

```html
<ul>
  <li class="skit-k">Kansai-ben (always shown)</li>
  <li class="skit-g">Kansai with inline grammar links</li>
  <li class="skit-w">Kansai with inline word links</li>
  <li class="skit-s">Standard Japanese</li>
  <li class="skit-e">English</li>
</ul>
```

Buttons `#skit-toggle-s-button`, `-e-button`, `-g-button`, `-w-button` toggle visibility of the corresponding `.skit-*` lines. The full rebuilt widget is ~30 lines of vanilla JS — no jQuery in the new build. Grammar / word links inside `.skit-g` and `.skit-w` lines point to `grammar_point` and `word` nodes respectively.

## Original sources

### Bazaar dumps (read-only reference)

- `/home/sjcarbon/local/src/bazaar/home/trunk/kansaibenkyou/` — the original Drupal 7 source tree:
  - `drupal/pixture_reloaded-2.2/` — original child theme (`kb.js`, `audio-player.js`, `kb.css`, `ruby.css`, `template.php`, `templates/`). Parent theme: `adaptivetheme`.
  - `mobile/` — jQuery-Mobile-based precursor to wrenshoe.
  - `ruby/`, `text_converter/`, `images/`, `aws/`.
- `/home/sjcarbon/local/src/bazaar/kb.net.shared/` — per-chapter lesson text, already pre-pivoted by language layer:
  - `NN.<title>.kansai.txt`, `.standard.txt`, `.english.txt`, `.grammar.txt`, `.word.txt`

### S3 buckets

Use the `kbnet-readonly` AWS profile. **Never inline-export the keys, never echo them into command output, never write them to memory or files.**

```sh
aws --profile kbnet-readonly s3 ls s3://kb-snapshot/
```

| Bucket | Size | Role |
|---|---|---|
| `kb-snapshot` | 172 MiB / 1789 obj | The mothballed Drupal page dump backing the CloudFront distribution `dcmkoqbweqigt.cloudfront.net` for `static.kansaibenkyou.net`. Includes `redo-lang.pl` and `redo-tax-term-links.pl` post-dump fixup scripts. |
| `kb-audio` | 86 MiB / 201 obj | Lesson audio. `ex_*` example conversations, `gr_*` grammar, `pho_kb_*` pronunciation. |
| `kb-image` | 55 MiB / 610 obj | Chapter images at multiple sizes (`_120`, `_160`, original); `banner/` (header carousel pool); `info/` icons. |
| `kb-mobile` | 1 MiB / 42 obj | Old jQuery Mobile deck. Confirmed redundant with wrenshoe `data/kansaiben.json`. |

`kb-scratch` and `kb-test-01` are effectively empty.

## Sister projects

- **Wrenshoe** (`/home/sjcarbon/local/src/git/wrenshoe/`) — canonical reference for LinkML schema patterns, source attribution conventions, and language-tag handling. Wrenshoe already hosts the `kb_net_vocab` deck (`data/kansaiben.json`) — the modern home for the kansai-ben vocabulary set, attributed to Keiko Yukawa and Seth Carbon under CC BY-SA 3.0.
- `wrenshoe.kansaibenkyou.net` will be a deployment of the wrenshoe app focused on the kansaiben deck (replacing the original `mobile.kansaibenkyou.net`).

## Dialect and content handling

- This site teaches **Kansai-ben (関西弁)**, not standard Japanese. Always preserve the distinction between Kansai-ben and standard Japanese (標準語 / hyōjungo). They are not interchangeable, and conflating them would defeat the site's pedagogical purpose.
- The `Stanza` model represents both layers explicitly (`kansai`, `standard`, `english`), plus the `_with_grammar_links` and `_with_word_links` overlays of the Kansai line.
- BCP 47 language tags used in this project:
  - `ja-x-kansai` for Kansai-ben.
  - `ja` for standard Japanese.
  - `en` for English translations.
- Grammar and vocabulary annotations come from the original author and should be treated as authoritative. When porting from the bazaar dumps, **do not "correct" or paraphrase** — preserve the original wording. If something looks wrong, surface it for human review rather than silently fixing it.

## Security: never commit secrets

**Never commit, log, echo, or memorize:**

- AWS access keys or secret access keys. Use the `kbnet-readonly` profile via `aws --profile kbnet-readonly ...` — never inline-export the keys, never paste them into commands or files.
- Private SSH keys; `.pem`, `.key`, `.p12`, `.pfx` files.
- Plaintext passwords, API tokens, OAuth secrets, signing keys.
- `.env`, `.envrc`, or any other dotenv-style files containing the above.
- Personal data of users or contributors beyond what they have publicly attributed.

**Always:**

- Stage files explicitly by name (`git add path/to/file`) rather than `git add -A` or `git add .` — that prevents accidental inclusion of stray temp files, credentials, or local test artifacts.
- Keep `_mothball/`, `*.local`, `*.secret`, `*.private`, `*.pem`, and `.env*` patterns in `.gitignore`.
- If a credential is accidentally committed, treat it as compromised and rotate it immediately, regardless of whether the commit was pushed.

## House rules for code

- Prefer editing existing files over creating new ones.
- Default to no comments. Only add a comment when the *why* is non-obvious — a hidden constraint, a workaround, a subtle invariant.
- No backwards-compatibility shims. There is no live deployment of this rebuild yet — change the code freely.
- For any data porting work: validate against the LinkML schema before committing the YAML.
- For UI work: actually serve the site locally and verify in a browser before declaring a task done.
- Stage files explicitly by name in commits (see Security above).
