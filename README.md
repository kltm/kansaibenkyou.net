# Kansaibenkyou.net

A learning resource for Kansai-ben (関西弁) — the family of Japanese
dialects spoken in the Kansai region (Osaka, Kyoto, Hyogo, Nara,
Wakayama, Shiga). Authored by Keiko Yukawa.

This repository hosts the rebuild of the original site (formerly a
Drupal 7 site, mothballed in 2016) as a Jekyll-based static site. The
canonical content lives as YAML in `data/`, validated against LinkML
schemas in `schema/`, and rendered by Jekyll templates in `_layouts/`.

The original mothballed site is still available at
<https://static.kansaibenkyou.net> while the rebuild is in progress.

## License

This repository is dual-licensed:

- **Site content** (lessons, audio, images, text, translations, grammar
  and vocabulary annotations, conversation scripts) is licensed under
  the [Creative Commons Attribution-ShareAlike 3.0 Unported
  License](https://creativecommons.org/licenses/by-sa/3.0/) (CC BY-SA
  3.0), © Keiko Yukawa.
- **Site code** (Jekyll templates, build tools, JavaScript, CSS,
  schemas) is licensed under the [BSD 3-Clause
  License](https://opensource.org/license/bsd-3-clause), © kltm.

See [`LICENSE`](LICENSE) for the full text of both.

## Status

Greenfield rebuild. See [`CLAUDE.md`](CLAUDE.md) for the in-depth
project brief — architecture decisions, the data model, original
sources, and house rules for contributors.
