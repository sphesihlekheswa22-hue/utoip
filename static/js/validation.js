/**
 * UITOP form validation helpers.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  var EMAIL_RE =
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  UITOP.validation = {
    isEmail: function (value) {
      return EMAIL_RE.test(String(value || "").trim());
    },

    isPassword: function (value, minLength) {
      minLength = minLength == null ? 8 : minLength;
      return String(value || "").length >= minLength;
    },

    markInvalid: function (field, message) {
      if (!field) return;
      field.setAttribute("aria-invalid", "true");
      field.classList.add("is-invalid");
      var id = field.getAttribute("data-error-id");
      var errorEl = id ? document.getElementById(id) : field.parentElement && field.parentElement.querySelector(".field-error");
      if (errorEl) errorEl.textContent = message || "";
    },

    clearInvalid: function (field) {
      if (!field) return;
      field.removeAttribute("aria-invalid");
      field.classList.remove("is-invalid");
      var id = field.getAttribute("data-error-id");
      var errorEl = id ? document.getElementById(id) : field.parentElement && field.parentElement.querySelector(".field-error");
      if (errorEl) errorEl.textContent = "";
    },
  };
})();
