/* Kansaibenkyou.net — skit toggle widget.
 *
 * Replaces the original Drupal pixture_reloaded theme's kb.js. Two
 * jobs:
 *
 *   1. Wire up the four "Show standard / English / grammar / words"
 *      buttons to toggle a corresponding `show-{s,e,g,w}` class on
 *      the parent .skit container. CSS handles the actual visibility.
 *
 *   2. On page load, walk every .skit-g and .skit-w line and convert
 *      `(NNN surface_text)` inline markers (inherited from the bazaar
 *      text format) into <a> links pointing at the relevant grammar
 *      point or word entry page. Multiple markers per line are
 *      supported.
 *
 * Vanilla JS, no dependencies. The original used jQuery + jQuery UI;
 * neither is needed.
 */

(function () {
  "use strict";

  var MARKER_RE = /\((\d+)([^)]+)\)/g;

  function renderLinks(li, kind) {
    // kind === "g" → grammar_points/<id>/
    // kind === "w" → words/<id>/
    var dest = kind === "g" ? "grammar_points" : "words";
    var raw = li.textContent;
    if (raw.indexOf("(") === -1) return;
    var html = "";
    var lastIndex = 0;
    var match;
    MARKER_RE.lastIndex = 0;
    while ((match = MARKER_RE.exec(raw)) !== null) {
      html += escapeHtml(raw.slice(lastIndex, match.index));
      var id = match[1];
      var text = match[2];
      html +=
        '<a class="skit-link skit-link-' + kind +
        '" href="/' + dest + "/" + id + '/">' +
        escapeHtml(text) + "</a>";
      lastIndex = MARKER_RE.lastIndex;
    }
    html += escapeHtml(raw.slice(lastIndex));
    li.innerHTML = html;
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function wireSkit(skit) {
    // Wire toggle buttons.
    var buttons = skit.querySelectorAll(".skit-toggle");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var layer = btn.dataset.layer;
        if (!layer) return;
        skit.classList.toggle("show-" + layer);
        btn.classList.toggle("is-active");
      });
    });

    // Render the (NNN ...) markers in grammar and word layers.
    skit.querySelectorAll(".skit-g").forEach(function (li) { renderLinks(li, "g"); });
    skit.querySelectorAll(".skit-w").forEach(function (li) { renderLinks(li, "w"); });
  }

  function init() {
    document.querySelectorAll(".skit").forEach(wireSkit);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
