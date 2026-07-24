/**
 * UITOP shared DOM & formatting utilities.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  UITOP.utils = {
    qs: function (sel, root) {
      return (root || document).querySelector(sel);
    },

    qsa: function (sel, root) {
      return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    },

    on: function (el, event, handler, opts) {
      if (!el) return function () {};
      el.addEventListener(event, handler, opts);
      return function () {
        el.removeEventListener(event, handler, opts);
      };
    },

    debounce: function (fn, wait) {
      var timer;
      wait = wait == null ? 200 : wait;
      return function () {
        var ctx = this;
        var args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function () {
          fn.apply(ctx, args);
        }, wait);
      };
    },

    formatDate: function (value, opts) {
      if (value == null || value === "") return "";
      var date = value instanceof Date ? value : new Date(value);
      if (isNaN(date.getTime())) return String(value);
      opts = opts || {};
      try {
        return new Intl.DateTimeFormat(opts.locale || undefined, {
          dateStyle: opts.dateStyle || "medium",
          timeStyle: opts.timeStyle,
        }).format(date);
      } catch (_) {
        return date.toLocaleDateString();
      }
    },

    toast: function (message, type, duration) {
      window.dispatchEvent(
        new CustomEvent("uitop:toast", {
          detail: {
            message: String(message || ""),
            type: type || "info",
            duration: duration == null ? 4000 : duration,
          },
        })
      );
    },
  };
})();
