/**
 * UITOP dashboard — charts, live KPIs, clock, activity pulse.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});
  var charts = {};
  var timers = [];

  function accent() {
    return (UITOP.charts && UITOP.charts.colors().accent) || "#0d9488";
  }

  function soft(c, a) {
    return UITOP.charts ? UITOP.charts.soft(c, a) : c;
  }

  function hours24() {
    var labels = [];
    for (var i = 0; i < 24; i += 2) {
      labels.push(String(i).padStart(2, "0") + ":00");
    }
    return labels;
  }

  function wave(base, amp, n, seed) {
    var out = [];
    for (var i = 0; i < n; i++) {
      out.push(
        Math.round(
          base +
            amp * Math.sin((i + seed) / 2.2) +
            amp * 0.35 * Math.cos((i + seed) / 1.4) +
            (Math.random() * 4 - 2)
        )
      );
    }
    return out;
  }

  function animateCount(el, target, suffix) {
    if (!el) return;
    var start = 0;
    var dur = 900;
    var t0 = performance.now();
    function frame(now) {
      var p = Math.min(1, (now - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      var val = Math.round(start + (target - start) * eased);
      el.textContent = val + (suffix || "");
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function tickClock() {
    var el = document.getElementById("dashClock");
    if (!el) return;
    var d = new Date();
    el.textContent = d.toLocaleTimeString("en-ZA", { hour12: false });
  }

  function dash() {
    return window.__DASHBOARD__ || { kpis: {}, charts: {} };
  }

  function buildInfra(range) {
    var live = dash().charts || {};
    if (live.infra_labels && live.infra_labels.length && range === "24h") {
      var a = accent();
      return {
        labels: live.infra_labels,
        datasets: [
          {
            label: "CPU %",
            data: live.infra_cpu || [],
            borderColor: a,
            backgroundColor: soft(a, 0.12),
            fill: true,
            tension: 0.4,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: "Memory %",
            data: live.infra_mem || [],
            borderColor: "#3b82f6",
            backgroundColor: soft("#3b82f6", 0.08),
            fill: true,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
        ],
      };
    }
    var labels;
    var n;
    if (range === "7d") {
      labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
      n = 7;
    } else if (range === "30d") {
      labels = [];
      for (var d = 1; d <= 30; d += 3) labels.push("D" + d);
      n = labels.length;
    } else {
      labels = hours24();
      n = labels.length;
    }
    var a2 = accent();
    return {
      labels: labels,
      datasets: [
        {
          label: "CPU %",
          data: wave(48, 16, n, 1),
          borderColor: a2,
          backgroundColor: soft(a2, 0.12),
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
        {
          label: "Memory %",
          data: wave(62, 12, n, 3),
          borderColor: "#3b82f6",
          backgroundColor: soft("#3b82f6", 0.08),
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
      ],
    };
  }

  function initSparks() {
    if (!UITOP.charts) return;
    charts.sparkDevices = UITOP.charts.createSparkline(
      document.getElementById("sparkDevices"),
      [180, 188, 192, 195, 201, 208, 214],
      "#10b981"
    );
    charts.sparkTickets = UITOP.charts.createSparkline(
      document.getElementById("sparkTickets"),
      [62, 58, 55, 52, 50, 48, 47],
      "#f59e0b"
    );
    charts.sparkBackup = UITOP.charts.createSparkline(
      document.getElementById("sparkBackup"),
      [90, 92, 91, 94, 95, 94, 96],
      accent()
    );
    charts.sparkAlerts = UITOP.charts.createSparkline(
      document.getElementById("sparkAlerts"),
      [5, 4, 6, 3, 4, 2, 2],
      "#ef4444"
    );
  }

  function initInfra() {
    var canvas = document.getElementById("infraChart");
    if (!canvas || !UITOP.charts) return;
    charts.infra = UITOP.charts.createLine(canvas, buildInfra("24h"), {
      scales: {
        y: { suggestedMax: 100, ticks: { callback: function (v) { return v + "%"; } } },
      },
    });
  }

  function initTickets() {
    var canvas = document.getElementById("ticketChart");
    if (!canvas || !UITOP.charts) return;
    var a = accent();
    var live = dash().charts || {};
    var labels = live.mix_labels || ["Open", "In progress", "Pending", "Resolved"];
    var values = live.mix_values || [18, 11, 9, 31];
    var data = {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: ["#0d9488", "#3b82f6", "#f59e0b", "#94a3b8", "#10b981"].slice(0, values.length),
          borderWidth: 0,
          hoverOffset: 6,
        },
      ],
    };
    charts.tickets = UITOP.charts.createDoughnut(canvas, data);
    var total = data.datasets[0].data.reduce(function (s, n) { return s + n; }, 0);
    var totalEl = document.getElementById("ticketTotal");
    if (totalEl) totalEl.textContent = String(total);
    var legend = document.getElementById("ticketLegend");
    if (legend) {
      legend.innerHTML = data.labels
        .map(function (label, i) {
          return (
            '<li><span class="swatch" style="background:' +
            data.datasets[0].backgroundColor[i] +
            '"></span><span>' +
            label +
            '</span><strong>' +
            data.datasets[0].data[i] +
            "</strong></li>"
          );
        })
        .join("");
    }
  }

  function initNetwork() {
    var canvas = document.getElementById("networkChart");
    if (!canvas || !UITOP.charts) return;
    var live = dash().charts || {};
    var labels = live.infra_labels && live.infra_labels.length ? live.infra_labels : ["now"];
    var cpu = live.infra_cpu && live.infra_cpu.length ? live.infra_cpu : [0];
    var mem = live.infra_mem && live.infra_mem.length ? live.infra_mem : [0];
    charts.network = UITOP.charts.createBar(
      canvas,
      {
        labels: labels,
        datasets: [
          {
            label: "CPU %",
            data: cpu,
            backgroundColor: soft(accent(), 0.85),
            borderRadius: 6,
            barPercentage: 0.55,
          },
          {
            label: "Memory %",
            data: mem,
            backgroundColor: soft("#3b82f6", 0.7),
            borderRadius: 6,
            barPercentage: 0.55,
          },
        ],
      },
      {
        scales: {
          x: { stacked: false },
          y: { suggestedMax: 100, ticks: { callback: function (v) { return v + "%"; } } },
        },
      }
    );
  }

  function initBackup() {
    var canvas = document.getElementById("backupChart");
    if (!canvas || !UITOP.charts) return;
    var k = dash().kpis || {};
    charts.backup = UITOP.charts.createBar(
      canvas,
      {
        labels: ["In use", "In store", "Requests", "Alerts"],
        datasets: [
          {
            label: "Count",
            data: [
              k.assets_assigned || 0,
              k.assets_store || 0,
              k.pending_requests || 0,
              k.open_alerts || 0,
            ],
            backgroundColor: [
              soft(accent(), 0.9),
              soft("#3b82f6", 0.75),
              soft("#f59e0b", 0.8),
              soft("#ef4444", 0.75),
            ],
            borderRadius: 8,
          },
        ],
      },
      { plugins: { legend: { display: false } } }
    );
  }

  function initDept() {
    var canvas = document.getElementById("deptChart");
    if (!canvas || !UITOP.charts) return;
    var live = dash().charts || {};
    var labels = live.dept_labels && live.dept_labels.length ? live.dept_labels : ["None"];
    var values = live.dept_values && live.dept_values.length ? live.dept_values : [0];
    charts.dept = UITOP.charts.createBar(
      canvas,
      {
        labels: labels,
        datasets: [
          {
            label: "Assets",
            data: values,
            backgroundColor: labels.map(function (_, i) {
              var colors = [accent(), "#3b82f6", "#f59e0b", "#94a3b8", "#10b981", "#8b5cf6"];
              return soft(colors[i % colors.length], 0.85);
            }),
            borderRadius: 8,
          },
        ],
      },
      { plugins: { legend: { display: false } } }
    );
  }

  function initAlertVelocity() {
    var canvas = document.getElementById("alertChart");
    if (!canvas || !UITOP.charts) return;
    var live = dash().charts || {};
    charts.alerts = UITOP.charts.createBar(
      canvas,
      {
        labels: live.alert_labels || ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        datasets: [
          {
            label: "Raised",
            data: live.alert_raised || [0, 0, 0, 0, 0, 0, 0],
            backgroundColor: soft("#ef4444", 0.8),
            borderRadius: 6,
          },
          {
            label: "Resolved",
            data: live.alert_resolved || [0, 0, 0, 0, 0, 0, 0],
            backgroundColor: soft(accent(), 0.85),
            borderRadius: 6,
          },
        ],
      }
    );
  }

  function initGauges() {
    if (!UITOP.charts) return;
    var a = accent();
    var k = dash().kpis || {};
    var pc = k.devices_total ? Math.round((k.devices_online / k.devices_total) * 100) : 0;
    var sc = k.servers_total ? Math.round((k.servers_online / k.servers_total) * 100) : 100;
    charts.gAd = UITOP.charts.createGauge(document.getElementById("gaugeAd"), pc || 0, a);
    charts.gErp = UITOP.charts.createGauge(document.getElementById("gaugeErp"), sc || 0, sc < 90 ? "#f59e0b" : a);
    charts.gSql = UITOP.charts.createGauge(document.getElementById("gaugeSql"), Math.min(100, (k.assets_total || 0) * 5), a);
    charts.gMail = UITOP.charts.createGauge(document.getElementById("gaugeMail"), Math.max(0, 100 - (k.pending_requests || 0) * 10), a);
    charts.gNet = UITOP.charts.createGauge(document.getElementById("gaugeNet"), Math.max(0, 100 - (k.open_alerts || 0) * 8), k.open_alerts ? "#f59e0b" : "#3b82f6");
  }

  function wireRange() {
    document.querySelectorAll(".chart-range .chip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".chart-range .chip").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        if (!charts.infra) return;
        var range = btn.getAttribute("data-range") || "24h";
        var next = buildInfra(range);
        charts.infra.data.labels = next.labels;
        charts.infra.data.datasets = next.datasets;
        charts.infra.update("active");
      });
    });
  }

  function livePulse() {
    // Nudge infra chart last point slightly
    if (charts.infra && charts.infra.data.datasets[0]) {
      charts.infra.data.datasets.forEach(function (ds) {
        var arr = ds.data;
        if (!arr.length) return;
        var last = arr[arr.length - 1];
        var next = Math.max(8, Math.min(96, last + (Math.random() * 6 - 3)));
        arr[arr.length - 1] = Math.round(next);
      });
      charts.infra.update("none");
    }

    var mem = document.getElementById("alertMem");
    if (mem) {
      var v = 89 + Math.round(Math.random() * 4);
      mem.textContent = String(v);
    }
    var age = document.getElementById("alertAge");
    if (age) age.textContent = "just now";
  }

  function injectActivity() {
    var feed = document.getElementById("activityFeed");
    if (!feed) return;
    var samples = [
      { icon: "fa-chart-line", title: "Latency spike cleared", meta: "Core LAN · 18ms", tone: "" },
      { icon: "fa-user-check", title: "User session approved", meta: "Finance VPN", tone: "" },
      { icon: "fa-shield-halved", title: "Firewall rule synced", meta: "FW-EDGE-01", tone: "" },
      { icon: "fa-rotate", title: "Restore test passed", meta: "File share NAS-01", tone: "" },
      { icon: "fa-bell", title: "Disk warning cleared", meta: "SQL-PROD-01", tone: "activity-icon--warning" },
    ];
    var s = samples[Math.floor(Math.random() * samples.length)];
    var li = document.createElement("li");
    li.className = "activity-item activity-item--new";
    li.innerHTML =
      '<span class="activity-icon ' +
      s.tone +
      '"><i class="fas ' +
      s.icon +
      '"></i></span>' +
      '<div class="activity-content"><div class="activity-title">' +
      s.title +
      '</div><div class="activity-meta">' +
      s.meta +
      '</div></div><span class="activity-time">now</span>';
    feed.insertBefore(li, feed.firstChild);
    while (feed.children.length > 8) feed.removeChild(feed.lastChild);
  }

  function initCounts() {
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseInt(el.getAttribute("data-count"), 10) || 0;
      // If parent has %, keep number only in this span
      animateCount(el, target, "");
    });
  }

  function destroyAll() {
    Object.keys(charts).forEach(function (k) {
      try {
        if (charts[k] && charts[k].destroy) charts[k].destroy();
      } catch (_) {}
    });
    charts = {};
    timers.forEach(clearInterval);
    timers = [];
  }

  var themeWired = false;

  UITOP.dashboard = {
    init: function () {
      if (!document.getElementById("infraChart")) return;
      destroyAll();
      tickClock();
      timers.push(setInterval(tickClock, 1000));
      initCounts();
      initSparks();
      initInfra();
      initTickets();
      initNetwork();
      initBackup();
      initDept();
      initAlertVelocity();
      initGauges();
      wireRange();
      timers.push(setInterval(livePulse, 4000));
      timers.push(setInterval(injectActivity, 9000));

      if (!themeWired) {
        themeWired = true;
        window.addEventListener("uitop:themechange", function () {
          UITOP.dashboard.init();
        });
      }
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", UITOP.dashboard.init);
  } else {
    UITOP.dashboard.init();
  }
})();
