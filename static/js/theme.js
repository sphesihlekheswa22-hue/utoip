/**
 * UITOP theme — data-theme + localStorage uitop-theme.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});
  var STORAGE_KEY = "uitop-theme";

  function icons() {
    return {
      sun: document.getElementById("theme-icon-sun"),
      moon: document.getElementById("theme-icon-moon"),
    };
  }

  function syncIcons(theme) {
    var dark = theme === "dark";
    var el = icons();
    if (el.sun) el.sun.style.display = dark ? "inline-block" : "none";
    if (el.moon) el.moon.style.display = dark ? "none" : "inline-block";
  }

  UITOP.theme = {
    get: function () {
      return localStorage.getItem(STORAGE_KEY) || "light";
    },

    set: function (theme) {
      theme = theme === "dark" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem(STORAGE_KEY, theme);
      syncIcons(theme);
      window.dispatchEvent(new CustomEvent("uitop:themechange", { detail: { theme: theme } }));
    },

    toggle: function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      UITOP.theme.set(next);
    },

    init: function () {
      UITOP.theme.set(UITOP.theme.get());
      var toggle = document.getElementById("theme-toggle");
      if (toggle) {
        toggle.addEventListener("click", UITOP.theme.toggle);
      }
    },
  };

  window.Theme = UITOP.theme;
})();
