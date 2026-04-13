(function () {
  "use strict";

  var MARKER_RE = /\((\d+)([^)]+)\)/g;
  var BASE = (document.querySelector('meta[name="baseurl"]') || {}).content || "";
  var SHOW_RE = /^show/i;

  function renderLinks(li, kind) {
    var dest = kind === "g" ? "grammar-points" : "words";
    var linkClass = kind === "g" ? "conv-link-emph-one" : "conv-link-emph-two";
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
        '<a class="' + linkClass +
        '" href="' + BASE + '/' + dest + "/" + id + '/">' +
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

  function setLayerVisible(skit, cls, visible) {
    skit.querySelectorAll("." + cls).forEach(function (el) {
      if (cls === "skit-k") {
        if (visible) { el.classList.remove("skit-hidden"); }
        else { el.classList.add("skit-hidden"); }
      } else {
        if (visible) { el.classList.add("skit-visible"); }
        else { el.classList.remove("skit-visible"); }
      }
    });
  }

  function setBtnLabel(btn, label) {
    btn.textContent = label;
  }

  function wireSkit(skit) {
    var btnS = skit.querySelector(".skit-toggle-s");
    var btnE = skit.querySelector(".skit-toggle-e");
    var btnG = skit.querySelector(".skit-toggle-g");
    var btnW = skit.querySelector(".skit-toggle-w");

    // Standard toggle — independent
    if (btnS) {
      btnS.addEventListener("click", function () {
        if (SHOW_RE.test(btnS.textContent)) {
          setLayerVisible(skit, "skit-s", true);
          setBtnLabel(btnS, "Hide Standard");
        } else {
          setLayerVisible(skit, "skit-s", false);
          setBtnLabel(btnS, "Show Standard");
        }
      });
    }

    // English toggle — independent
    if (btnE) {
      btnE.addEventListener("click", function () {
        if (SHOW_RE.test(btnE.textContent)) {
          setLayerVisible(skit, "skit-e", true);
          setBtnLabel(btnE, "Hide English");
        } else {
          setLayerVisible(skit, "skit-e", false);
          setBtnLabel(btnE, "Show English");
        }
      });
    }

    // Grammar toggle — mutually exclusive with Words, replaces bare Kansai
    if (btnG) {
      btnG.addEventListener("click", function () {
        if (SHOW_RE.test(btnG.textContent)) {
          setLayerVisible(skit, "skit-g", true);
          setLayerVisible(skit, "skit-k", false);
          setLayerVisible(skit, "skit-w", false);
          setBtnLabel(btnG, "Hide Grammar");
          if (btnW) setBtnLabel(btnW, "Show Words");
        } else {
          setLayerVisible(skit, "skit-k", true);
          setLayerVisible(skit, "skit-g", false);
          setLayerVisible(skit, "skit-w", false);
          setBtnLabel(btnG, "Show Grammar");
          if (btnW) setBtnLabel(btnW, "Show Words");
        }
      });
    }

    // Words toggle — mutually exclusive with Grammar, replaces bare Kansai
    if (btnW) {
      btnW.addEventListener("click", function () {
        if (SHOW_RE.test(btnW.textContent)) {
          setLayerVisible(skit, "skit-w", true);
          setLayerVisible(skit, "skit-k", false);
          setLayerVisible(skit, "skit-g", false);
          setBtnLabel(btnW, "Hide Words");
          if (btnG) setBtnLabel(btnG, "Show Grammar");
        } else {
          setLayerVisible(skit, "skit-k", true);
          setLayerVisible(skit, "skit-w", false);
          setLayerVisible(skit, "skit-g", false);
          setBtnLabel(btnW, "Show Words");
          if (btnG) setBtnLabel(btnG, "Show Grammar");
        }
      });
    }

    // Render inline markers as links
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
