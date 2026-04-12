---
layout: default
title: Kansaibenkyou.net
---

# Kansaibenkyou.net

A learning resource for Kansai-ben (関西弁), the family of Japanese
dialects spoken in the Kansai region — Osaka, Kyoto, Hyogo, Nara,
Wakayama, Shiga. Authored by Keiko Yukawa.

## Example conversations

{% for conv in site.conversations %}
- [{{ conv.title }}]({{ conv.url | relative_url }})
{% endfor %}

## Real conversations

{% for rc in site.real_conversations %}
- [{{ rc.title }}]({{ rc.url | relative_url }})
{% endfor %}

## Sections

- [Introduction](/intro/)
- [What is Kansai-ben?](/what/)
- [Grammar](/grammar/)
- [Vocabulary](/words/)
- [Pronunciation](/pronunciation/)
- [Resources](/resources/)
- [Bibliography](/bibliography/)
- [About](/about/)
- [Copyright](/copyright/)
