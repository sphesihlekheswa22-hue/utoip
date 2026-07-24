(function () {
  const form = document.getElementById("login-form");
  const toggle = document.getElementById("toggle-password");
  const password = document.getElementById("password");
  const submit = document.getElementById("login-submit");

  if (toggle && password) {
    toggle.addEventListener("click", function () {
      const showing = password.type === "text";
      password.type = showing ? "password" : "text";
      toggle.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      const icon = toggle.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-eye", showing);
        icon.classList.toggle("fa-eye-slash", !showing);
      }
    });
  }

  if (form && submit) {
    form.addEventListener("submit", function () {
      const email = document.getElementById("email");
      if (!email?.value || !password?.value) return;
      submit.disabled = true;
      const label = submit.querySelector(".login-submit-label");
      const busy = submit.querySelector(".login-submit-busy");
      if (label) label.hidden = true;
      if (busy) busy.hidden = false;
    });
  }

  const year = document.getElementById("uitop-year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
