(function () {
  "use strict";

  document.querySelectorAll("table.sortable").forEach(function (table) {
    var headers = table.querySelectorAll("thead th");
    headers.forEach(function (th, colIndex) {
      th.style.cursor = "pointer";
      th.title = "Click to sort";
      th.addEventListener("click", function () {
        var tbody = table.querySelector("tbody");
        var rows = Array.from(tbody.querySelectorAll("tr"));
        var ascending = th.dataset.sortDir !== "asc";

        rows.sort(function (a, b) {
          var aText = (a.cells[colIndex] || {}).textContent || "";
          var bText = (b.cells[colIndex] || {}).textContent || "";
          return ascending
            ? aText.localeCompare(bText, "ja")
            : bText.localeCompare(aText, "ja");
        });

        rows.forEach(function (row) { tbody.appendChild(row); });

        headers.forEach(function (h) { delete h.dataset.sortDir; });
        th.dataset.sortDir = ascending ? "asc" : "desc";
      });
    });
  });
})();
