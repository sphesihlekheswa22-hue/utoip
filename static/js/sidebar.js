/**
 * UITOP mobile sidebar — menu button, dimmer, Escape, link close.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  var btn;
  var dimmer;
  var sidebar;

  function isMobile() {
    return window.matchMedia("(max-width: 1023px)").matches;
  }

  function setOpen(open) {
    document.body.classList.toggle("has-sidebar-open", open);
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (dimmer) dimmer.classList.toggle("is-visible", open);
  }

  UITOP.sidebar = {
    open: function () {
      setOpen(true);
    },
    close: function () {
      setOpen(false);
    },
    toggle: function () {
      setOpen(!document.body.classList.contains("has-sidebar-open"));
    },
    init: function () {
      btn = document.getElementById("uitop-menu-btn");
      dimmer = document.getElementById("uitop-dimmer");
      sidebar = document.getElementById("uitop-sidebar");
      if (!btn || !sidebar) return;

      btn.addEventListener("click", UITOP.sidebar.toggle);

      if (dimmer) {
        dimmer.addEventListener("click", UITOP.sidebar.close);
      }

      sidebar.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          if (isMobile()) UITOP.sidebar.close();
        });
      });

      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && document.body.classList.contains("has-sidebar-open")) {
          UITOP.sidebar.close();
          btn.focus();
        }
      });
    },
  };

  window.Sidebar = UITOP.sidebar;
})();
