/**
 * UITOP table search — filter rows via [data-table-search].
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function resolveTable(input) {
    var tableId = input.getAttribute("data-table-search");
    if (tableId) return document.getElementById(tableId);
    return input.closest(".panel, section, .table-wrap, main") &&
      input.closest(".panel, section, .table-wrap, main").querySelector("table");
  }

  function filterTable(input) {
    var table = resolveTable(input);
    if (!table || !table.tBodies.length) return;

    var query = String(input.value || "").trim().toLowerCase();
    var rows = table.tBodies[0].rows;

    for (var i = 0; i < rows.length; i++) {
      var text = rows[i].textContent || "";
      rows[i].style.display = !query || text.toLowerCase().indexOf(query) !== -1 ? "" : "none";
    }
  }

  function bind(input) {
    var handler = UITOP.utils ? UITOP.utils.debounce(function () {
      filterTable(input);
    }, 150) : function () {
      filterTable(input);
    };
    input.addEventListener("input", handler);
    input.addEventListener("search", handler);
  }

  UITOP.tables = {
    init: function () {
      var inputs = document.querySelectorAll("[data-table-search]");
      for (var i = 0; i < inputs.length; i++) bind(inputs[i]);
    },
  };
})();
