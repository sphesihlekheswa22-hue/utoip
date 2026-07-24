/**
 * UITOP forms — required field validation on [data-validate].
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function validateField(field) {
    var validation = UITOP.validation;
    if (!field) return true;

    var value = field.type === "checkbox" ? field.checked : String(field.value || "").trim();
    var type = field.getAttribute("data-validate-type");
    var label = field.getAttribute("aria-label") || field.name || "This field";
    var ok = true;
    var message = "";

    if (field.hasAttribute("required")) {
      if (field.type === "checkbox" && !value) {
        ok = false;
        message = label + " is required.";
      } else if (!value) {
        ok = false;
        message = label + " is required.";
      }
    }

    if (ok && value && type === "email" && validation && !validation.isEmail(value)) {
      ok = false;
      message = "Enter a valid email address.";
    }

    if (ok && value && type === "password" && validation && !validation.isPassword(value)) {
      ok = false;
      message = "Password must be at least 8 characters.";
    }

    if (validation) {
      if (ok) validation.clearInvalid(field);
      else validation.markInvalid(field, message);
    }

    return ok;
  }

  function validateForm(form) {
    var fields = form.querySelectorAll("input, select, textarea");
    var valid = true;
    for (var i = 0; i < fields.length; i++) {
      if (!validateField(fields[i])) valid = false;
    }
    return valid;
  }

  function bind(form) {
    form.addEventListener("submit", function (e) {
      if (!validateForm(form)) {
        e.preventDefault();
        var firstInvalid = form.querySelector("[aria-invalid='true']");
        if (firstInvalid) firstInvalid.focus();
      }
    });

    form.querySelectorAll("input, select, textarea").forEach(function (field) {
      field.addEventListener("blur", function () {
        validateField(field);
      });
    });
  }

  UITOP.forms = {
    init: function () {
      document.querySelectorAll("form[data-validate]").forEach(bind);
    },
    validateField: validateField,
    validateForm: validateForm,
  };
})();
