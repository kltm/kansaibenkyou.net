---
layout: single
title: Welcome to Kansaibenkyou.net!
sidebar:
  nav: "site-nav"
header:
  overlay_image: /assets/banner/242.jpg
  overlay_filter: 0.3
  caption: "Welcome to Kansai!"
---

{% assign home = site.data.pages.page_4 %}
{% if home.body %}
  {% if site.baseurl != "" %}
    {% assign link_prefix = '](' | append: site.baseurl | append: '/' %}
    {% assign img_prefix = 'src="' | append: site.baseurl | append: '/' %}
    {% assign body_fixed = home.body | replace: '](/', link_prefix | replace: 'src="/', img_prefix %}
  {% else %}
    {% assign body_fixed = home.body %}
  {% endif %}
  <div class="home-content-box">
  {{ body_fixed | markdownify }}
  </div>
{% endif %}
