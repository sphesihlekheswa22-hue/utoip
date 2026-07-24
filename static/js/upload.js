/**
 * UITOP upload zones — drag-drop highlight for [data-upload].
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function bind(zone) {
    var input = zone.querySelector('input[type="file"]');

    zone.addEventListener("dragenter", function (e) {
      e.preventDefault();
      zone.classList.add("is-dragover");
    });

    zone.addEventListener("dragover", function (e) {
      e.preventDefault();
      zone.classList.add("is-dragover");
    });

    zone.addEventListener("dragleave", function (e) {
      if (e.currentTarget.contains(e.relatedTarget)) return;
      zone.classList.remove("is-dragover");
    });

    zone.addEventListener("drop", function (e) {
      e.preventDefault();
      zone.classList.remove("is-dragover");
      if (!input || !e.dataTransfer || !e.dataTransfer.files.length) return;
      input.files = e.dataTransfer.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    zone.addEventListener("click", function (e) {
      if (e.target === input) return;
      if (input) input.click();
    });
  }

  UITOP.upload = {
    init: function () {
      document.querySelectorAll("[data-upload]").forEach(bind);
    },
  };
})();
