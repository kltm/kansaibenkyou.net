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
  {%- assign href_prefix = 'href="' | append: site.baseurl | append: '/' -%}
  {%- assign src_prefix = 'src="' | append: site.baseurl | append: '/' -%}
  {%- assign body_fixed = home.body | replace: 'href="/', href_prefix | replace: 'src="/', src_prefix -%}
  <div class="home-content-box">
  {{ body_fixed }}
  </div>
{% endif %}
