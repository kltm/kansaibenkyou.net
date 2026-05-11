// Replace the legacy <p class="kb-audio"><a href="...mp3">[↓]</a></p>
// stubs (originally driven by the Drupal site's Flash audio player) with
// native HTML5 <audio controls> elements so the sound plays inline
// instead of navigating away to the bare mp3 file.
//
// The mothball YAML keeps the original <p class="kb-audio"> markup
// verbatim per the SoT rule; this replacement is render-side only and
// runs once per page load.

(function () {
  function init() {
    var nodes = document.querySelectorAll("p.kb-audio");
    for (var i = 0; i < nodes.length; i++) {
      var p = nodes[i];
      var a = p.querySelector('a[href*=".mp3"], a[href*=".ogg"], a[href*=".wav"]');
      if (!a) continue;
      var audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = a.getAttribute("href");
      audio.className = "kb-audio-inline";
      // Preserve the original p's id (e.g., audioplayer-1) so the
      // mothball-era anchors and any future hash-targeting still work.
      if (p.id) audio.id = p.id;
      p.parentNode.replaceChild(audio, p);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
