/**
 * UITOP AI chat widget toggle — #ai-widget.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function widget() {
    return document.getElementById("ai-widget");
  }

  UITOP.ai = {
    open: function () {
      var el = widget();
      if (!el) return;
      el.classList.add("is-open");
      el.setAttribute("aria-hidden", "false");
    },
    close: function () {
      var el = widget();
      if (!el) return;
      el.classList.remove("is-open");
      el.setAttribute("aria-hidden", "true");
    },
    toggle: function () {
      var el = widget();
      if (!el) return;
      if (el.classList.contains("is-open")) UITOP.ai.close();
      else UITOP.ai.open();
    },
    init: function () {
      var el = widget();
      if (!el) return;

      document.addEventListener("click", function (e) {
        if (e.target.closest("[data-ai-toggle]")) {
          e.preventDefault();
          UITOP.ai.toggle();
          return;
        }
        if (e.target.closest("[data-ai-close]")) {
          e.preventDefault();
          UITOP.ai.close();
        }
      });

      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && el.classList.contains("is-open")) UITOP.ai.close();
      });
    },
  };
})();
