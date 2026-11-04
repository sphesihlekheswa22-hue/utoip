/**
 * IT Copilot — floating widget + full page chat for UITOP.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  var state = {
    sessionId: null,
    busy: false,
    mode: "widget", // widget | page
  };

  function $(id) {
    return document.getElementById(id);
  }

  function els() {
    if (state.mode === "page") {
      return {
        root: $("copilot-page"),
        body: $("copilot-page-body"),
        messages: $("copilot-page-messages"),
        welcome: $("copilot-page-welcome"),
        typing: $("copilot-page-typing"),
        input: $("copilot-page-input"),
        form: $("copilot-page-form"),
      };
    }
    return {
      root: $("ai-widget"),
      body: $("copilot-body"),
      messages: $("copilot-messages"),
      welcome: $("copilot-welcome"),
      typing: $("copilot-typing"),
      input: $("copilot-input"),
      form: $("copilot-form"),
    };
  }

  function renderMarkdown(text) {
    if (!text) return "";
    var html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Simple markdown tables
    html = html.replace(/(?:^|\n)((?:\|.+\|(?:\n|$))+)/g, function (_m, block) {
      var lines = block.trim().split("\n").filter(Boolean);
      if (lines.length < 2) return block;
      var rows = lines.filter(function (line, idx) {
        return idx !== 1 || !/^\|?\s*-+/.test(line.replace(/\|/g, "|"));
      });
      // Drop separator row like |---|---|
      rows = lines.filter(function (line) {
        return !/^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(line.trim());
      });
      if (rows.length < 1) return block;
      var out = "<table><tbody>";
      rows.forEach(function (line, i) {
        var cells = line.replace(/^\|/, "").replace(/\|$/, "").split("|");
        var tag = i === 0 ? "th" : "td";
        out += "<tr>" + cells.map(function (c) {
          return "<" + tag + ">" + c.trim() + "</" + tag + ">";
        }).join("") + "</tr>";
      });
      out += "</tbody></table>";
      return "\n" + out + "\n";
    });

    html = html
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/^[-*] (.+)$/gm, "<li>$1</li>")
      .replace(/\n/g, "<br>");
    html = html.replace(/(<li>.*?<\/li>)(<br>)*(<li>)/g, "$1$3");
    html = html.replace(/(<li>[\s\S]*?<\/li>)+/g, function (m) {
      return "<ul>" + m + "</ul>";
    });
    // Clean breaks around tables
    html = html.replace(/<br>\s*<table>/g, "<table>").replace(/<\/table>\s*<br>/g, "</table>");
    return html;
  }

  function setChatting(on) {
    var page = $("copilot-page");
    if (!page) return;
    if (on) page.classList.add("is-chatting");
    else page.classList.remove("is-chatting");
  }

  function appendMessage(role, content) {
    var e = els();
    if (!e.messages) return;
    var el = document.createElement("div");
    el.className = "copilot-msg copilot-msg--" + role;
    if (role === "assistant") {
      el.innerHTML =
        '<span class="copilot-avatar-sm"><i class="fas fa-robot"></i></span>' +
        '<div class="copilot-bubble">' +
        renderMarkdown(content) +
        "</div>";
    } else {
      el.innerHTML =
        '<div class="copilot-bubble copilot-bubble--user">' +
        renderMarkdown(content) +
        "</div>" +
        '<span class="copilot-avatar-sm copilot-avatar-sm--user"><i class="fas fa-user"></i></span>';
    }
    e.messages.appendChild(el);
    if (e.body) e.body.scrollTop = e.body.scrollHeight;
    if (e.welcome) e.welcome.style.display = "none";
    setChatting(true);
  }

  function showTyping() {
    var e = els();
    if (e.typing) e.typing.hidden = false;
    if (e.body) e.body.scrollTop = e.body.scrollHeight;
  }

  function hideTyping() {
    var e = els();
    if (e.typing) e.typing.hidden = true;
  }

  function sendQuestion(question) {
    if (state.busy || !question || !question.trim()) return;
    state.busy = true;
    appendMessage("user", question);
    showTyping();

    fetch("/ai/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question: question, session_id: state.sessionId }),
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        hideTyping();
        if (!result.ok) {
          var msg =
            (result.data && result.data.error) ||
            "Request failed (" + result.status + "). You may not have permission, or the server needs a restart.";
          appendMessage("assistant", msg);
          return;
        }
        if (result.data.session_id) {
          state.sessionId = result.data.session_id;
          var page = $("copilot-page");
          if (page) page.setAttribute("data-session-id", String(result.data.session_id));
        }
        appendMessage("assistant", result.data.answer || "No response.");
      })
      .catch(function (err) {
        hideTyping();
        appendMessage(
          "assistant",
          "Network error — please check your connection and try again."
        );
        console.error("Copilot error:", err);
      })
      .finally(function () {
        state.busy = false;
      });
  }

  function resetChat() {
    state.sessionId = null;
    state.busy = false;
    var e = els();
    if (e.messages) e.messages.innerHTML = "";
    if (e.welcome) e.welcome.style.display = "";
    if (e.input) {
      e.input.value = "";
      e.input.style.height = "auto";
    }
    hideTyping();
    setChatting(false);
    document.querySelectorAll(".copilot-session-item.is-active").forEach(function (n) {
      n.classList.remove("is-active");
    });
    var page = $("copilot-page");
    if (page) page.setAttribute("data-session-id", "");
  }

  function loadSession(sessionId) {
    if (!sessionId) return;
    fetch("/ai/sessions/" + sessionId + "/messages", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (msgs) {
        state.sessionId = sessionId;
        setChatting(true);
        document.querySelectorAll(".copilot-session-item").forEach(function (n) {
          n.classList.toggle("is-active", n.getAttribute("data-session-id") === String(sessionId));
        });
        var e = els();
        if (e.messages) e.messages.innerHTML = "";
        if (e.welcome) e.welcome.style.display = "none";
        (msgs || []).forEach(function (m) {
          appendMessage(m.role, m.content);
        });
      })
      .catch(function () {
        appendMessage("assistant", "Could not load that conversation.");
      });
  }

  function bindForm(form, input) {
    if (!form || !input) return;

    input.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 140) + "px";
    });

    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        form.requestSubmit();
      }
    });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var q = input.value.trim();
      if (!q) return;
      input.value = "";
      input.style.height = "auto";
      sendQuestion(q);
    });
  }

  UITOP.ai = {
    open: function () {
      var el = $("ai-widget");
      if (!el) return;
      el.classList.add("is-open");
      el.setAttribute("aria-hidden", "false");
      var inp = $("copilot-input");
      if (inp) setTimeout(function () { inp.focus(); }, 120);
    },
    close: function () {
      var el = $("ai-widget");
      if (!el) return;
      el.classList.remove("is-open");
      el.setAttribute("aria-hidden", "true");
    },
    toggle: function () {
      var el = $("ai-widget");
      if (!el) return;
      if (el.classList.contains("is-open")) UITOP.ai.close();
      else UITOP.ai.open();
    },
    ask: function (question) {
      if ($("copilot-page")) {
        state.mode = "page";
        sendQuestion(question);
      } else {
        UITOP.ai.open();
        state.mode = "widget";
        sendQuestion(question);
      }
    },
    init: function () {
      var el = $("ai-widget");
      if (!el) return;

      document.addEventListener("click", function (e) {
        if (e.target.closest("[data-ai-toggle]")) {
          e.preventDefault();
          UITOP.ai.toggle();
          return;
        }
        if (e.target.closest("[data-ai-close]")) {
          e.preventDefault();
          UITOP.ai.close();
          return;
        }
        var suggestion = e.target.closest("#ai-widget .copilot-suggestion");
        if (suggestion) {
          state.mode = "widget";
          var prompt = suggestion.getAttribute("data-prompt");
          if (prompt) sendQuestion(prompt);
          return;
        }
        if (e.target.closest("#copilot-new-chat")) {
          state.mode = "widget";
          resetChat();
        }
      });

      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && el.classList.contains("is-open")) UITOP.ai.close();
      });

      bindForm($("copilot-form"), $("copilot-input"));
    },
    initPage: function () {
      if (!$("copilot-page")) return;
      state.mode = "page";

      bindForm($("copilot-page-form"), $("copilot-page-input"));

      var newBtn = $("copilot-page-new");
      if (newBtn) {
        newBtn.addEventListener("click", function () {
          state.mode = "page";
          resetChat();
        });
      }

      document.addEventListener("click", function (e) {
        var suggestion = e.target.closest("#copilot-page .copilot-suggestion, #copilot-page .copilot-cap, #copilot-page .copilot-prompt-card, #copilot-page .copilot-prompt-primary");
        if (suggestion) {
          state.mode = "page";
          var prompt = suggestion.getAttribute("data-prompt");
          if (prompt) sendQuestion(prompt);
          return;
        }
        var item = e.target.closest(".copilot-session-item");
        if (item) {
          state.mode = "page";
          loadSession(item.getAttribute("data-session-id"));
        }
      });

      var pageInput = $("copilot-page-input");
      if (pageInput) pageInput.focus();
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", UITOP.ai.init);
  } else {
    UITOP.ai.init();
  }
})();
