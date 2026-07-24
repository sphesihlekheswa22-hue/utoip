/**
 * UITOP toast notifications — listens for uitop:toast events.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});
  var utils = UITOP.utils;

  function container() {
    return document.querySelector(".uitop-toast-container");
  }

  function dismiss(toast) {
    if (!toast || !toast.parentNode) return;
    toast.classList.add("is-leaving");
    setTimeout(function () {
      toast.remove();
    }, 180);
  }

  function showToast(detail) {
    var root = container();
    if (!root) return;

    detail = detail || {};
    var type = detail.type || "info";
    var toast = document.createElement("div");
    toast.className = "uitop-toast uitop-toast--" + type;
    toast.setAttribute("role", type === "error" ? "alert" : "status");

    var text = document.createElement("span");
    text.textContent = detail.message || "";
    toast.appendChild(text);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "uitop-toast-close";
    close.setAttribute("aria-label", "Dismiss");
    close.innerHTML = "&times;";
    close.addEventListener("click", function () {
      dismiss(toast);
    });
    toast.appendChild(close);

    root.appendChild(toast);

    var duration = detail.duration == null ? 4000 : detail.duration;
    if (duration > 0) {
      setTimeout(function () {
        dismiss(toast);
      }, duration);
    }
  }

  UITOP.notifications = {
    show: showToast,
    init: function () {
      window.addEventListener("uitop:toast", function (e) {
        showToast(e.detail);
      });
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", UITOP.notifications.init);
  } else {
    UITOP.notifications.init();
  }
})();
