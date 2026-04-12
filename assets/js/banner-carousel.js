(function () {
  "use strict";

  var el = document.getElementById("banner-image");
  if (!el) return;

  var base = (document.querySelector('meta[name="baseurl"]') || {}).content || "";

  fetch(base + "/assets/banner/manifest.json")
    .then(function (r) { return r.json(); })
    .then(function (images) {
      if (!images.length) return;
      var pick = images[Math.floor(Math.random() * images.length)];
      el.src = base + "/assets/banner/" + pick;
      el.alt = "Welcome to Kansai!";
      el.style.opacity = "1";
    });
})();
