---
layout: default
title: Kansaibenkyou.net
---

# Kansaibenkyou.net

A learning resource for Kansai-ben (関西弁), the family of Japanese
dialects spoken in the Kansai region — Osaka, Kyoto, Hyogo, Nara,
Wakayama, Shiga. Authored by Keiko Yukawa.

This is a rebuild in progress of the original site. Most content is
still being ported. The mothballed reference site is at
<https://static.kansaibenkyou.net> while work continues here.

## Example conversations

{% for conv in site.conversations %}
- [{{ conv.title }}]({{ conv.url | relative_url }})
{% endfor %}
