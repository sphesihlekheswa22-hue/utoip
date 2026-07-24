/**
 * UITOP global search shortcut — / focuses topbar search.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function isEditable(target) {
    if (!target) return false;
    var tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
  }

  UITOP.search = {
    focus: function () {
      var input = document.querySelector(".uitop-topbar-search input");
      if (input) input.focus();
    },
    init: function () {
      document.addEventListener("keydown", function (e) {
        if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
        if (isEditable(e.target)) return;
        e.preventDefault();
        UITOP.search.focus();
      });
    },
  };
})();
