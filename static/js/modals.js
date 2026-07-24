/**
 * UITOP modals — open/close via [data-modal].
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function modalFor(name) {
    if (!name) return null;
    return document.getElementById(name) || document.querySelector('[data-modal-id="' + name + '"]');
  }

  function setOpen(modal, open) {
    if (!modal) return;
    modal.classList.toggle("is-open", open);
    modal.setAttribute("aria-hidden", open ? "false" : "true");
    document.body.classList.toggle("has-modal-open", !!document.querySelector(".uitop-modal.is-open, [data-modal-id].is-open"));
    if (open) {
      var focusable = modal.querySelector("[autofocus], button, input, select, textarea, a[href]");
      if (focusable) focusable.focus();
    }
  }

  UITOP.modals = {
    open: function (name) {
      setOpen(modalFor(name), true);
    },
    close: function (name) {
      var modal = typeof name === "string" ? modalFor(name) : name;
      setOpen(modal, false);
    },
    init: function () {
      document.addEventListener("click", function (e) {
        var closer = e.target.closest("[data-modal-close]");
        if (closer) {
          e.preventDefault();
          var parentModal = closer.closest(".uitop-modal, [data-modal-id]");
          UITOP.modals.close(parentModal || closer.getAttribute("data-modal-close"));
          return;
        }

        var trigger = e.target.closest("[data-modal]");
        if (!trigger) return;

        if (trigger.classList.contains("uitop-modal") || trigger.hasAttribute("data-modal-id")) {
          if (e.target === trigger) UITOP.modals.close(trigger);
          return;
        }

        e.preventDefault();
        UITOP.modals.open(trigger.getAttribute("data-modal"));
      });

      document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        document.querySelectorAll(".uitop-modal.is-open, [data-modal-id].is-open").forEach(function (modal) {
          UITOP.modals.close(modal);
        });
      });
    },
  };
})();
