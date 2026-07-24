/**
 * UITOP shell — Alpine app store + boot.
 *
 * Script load order (no build step; use defer on each tag):
 *   1. utils.js
 *   2. validation.js
 *   3. charts.js
 *   4. notifications.js
 *   5. theme.js
 *   6. sidebar.js
 *   7. search.js
 *   8. modals.js
 *   9. forms.js
 *  10. tables.js
 *  11. upload.js
 *  12. ai.js
 *  13. app.js
 *  Page scripts last (e.g. dashboard.js). Alpine CDN after app.js.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  var STORAGE_KEYS = {
    access: "uitop_access_token",
    refresh: "uitop_refresh_token",
    user: "uitop_user",
    permissions: "uitop_permissions",
  };

  function getCookie(name) {
    var parts = String(document.cookie || "").split(";");
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      var idx = part.indexOf("=");
      if (idx === -1) continue;
      var key = part.slice(0, idx).trim();
      if (key !== name) continue;
      try {
        return decodeURIComponent(part.slice(idx + 1).trim());
      } catch (_) {
        return part.slice(idx + 1).trim();
      }
    }
    return null;
  }

  function getAccessToken() {
    return (
      localStorage.getItem(STORAGE_KEYS.access) ||
      localStorage.getItem("access_token") ||
      getCookie("uitop_access_token")
    );
  }

  function readUser() {
    try {
      var raw = localStorage.getItem(STORAGE_KEYS.user);
      return raw ? JSON.parse(raw) : null;
    } catch (_) {
      return null;
    }
  }

  function initialsFrom(user) {
    if (!user) return "IT";
    var name = user.name || user.full_name || user.email || "IT";
    var parts = String(name).trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return String(name).slice(0, 2).toUpperCase();
  }

  function clearSession() {
    [
      STORAGE_KEYS.access,
      STORAGE_KEYS.refresh,
      STORAGE_KEYS.user,
      STORAGE_KEYS.permissions,
      "access_token",
      "refresh_token",
    ].forEach(function (k) {
      localStorage.removeItem(k);
    });
    document.cookie = "uitop_access_token=; path=/; Max-Age=0; SameSite=Lax";
  }

  var API_BASE_URL = window.API_BASE_URL || "";
  var API_BASE = API_BASE_URL + "/api/v1";

  window.app = function app(opts) {
    opts = opts || {};
    var stored = readUser();

    return {
      currentPage: opts.currentPage || "dashboard",
      unreadCount: 0,
      user: {
        name: (stored && (stored.name || stored.full_name)) || "Admin",
        role: (stored && (stored.role || stored.role_name)) || "Administrator",
        email: (stored && stored.email) || "",
      },
      get userInitials() {
        return initialsFrom(this.user);
      },
      init: function () {
        var refreshed = readUser();
        if (refreshed) {
          this.user.name = refreshed.name || refreshed.full_name || this.user.name;
          this.user.role = refreshed.role || refreshed.role_name || this.user.role;
          this.user.email = refreshed.email || this.user.email;
        }
      },
      logout: function () {
        var token = getAccessToken();
        var done = function () {
          clearSession();
          window.location.assign("/login");
        };
        if (!token) {
          done();
          return;
        }
        fetch(API_BASE + "/auth/logout", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            Authorization: "Bearer " + token,
          },
        })
          .catch(function () {})
          .then(done);
      },
    };
  };

  UITOP.API_BASE = API_BASE;
  UITOP.getAccessToken = getAccessToken;
  UITOP.clearSession = clearSession;
  UITOP.readUser = readUser;

  function bootYear() {
    var yearEl = document.getElementById("uitop-year");
    if (yearEl) yearEl.textContent = String(new Date().getFullYear());
  }

  function bootShell() {
    bootYear();
    if (UITOP.theme && UITOP.theme.init) UITOP.theme.init();
    if (UITOP.sidebar && UITOP.sidebar.init) UITOP.sidebar.init();
    if (UITOP.search && UITOP.search.init) UITOP.search.init();
    if (UITOP.modals && UITOP.modals.init) UITOP.modals.init();
    if (UITOP.forms && UITOP.forms.init) UITOP.forms.init();
    if (UITOP.tables && UITOP.tables.init) UITOP.tables.init();
    if (UITOP.upload && UITOP.upload.init) UITOP.upload.init();
    if (UITOP.ai && UITOP.ai.init) UITOP.ai.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootShell);
  } else {
    bootShell();
  }
})();
