/**
 * UITOP Chart.js helpers — line, doughnut, bar, gauge.
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function themeColors() {
    var style = getComputedStyle(document.documentElement);
    return {
      accent: style.getPropertyValue("--accent").trim() || "#0d9488",
      text: style.getPropertyValue("--text-secondary").trim() || "#64748b",
      muted: style.getPropertyValue("--text-muted").trim() || "#94a3b8",
      border: style.getPropertyValue("--border-default").trim() || "rgba(15,23,42,0.08)",
      bg: style.getPropertyValue("--bg-elevated").trim() || "#ffffff",
    };
  }

  function soft(color, alpha) {
    // Chart.js accepts rgba strings; approximate from hex when possible
    if (color.indexOf("#") === 0 && color.length === 7) {
      var r = parseInt(color.slice(1, 3), 16);
      var g = parseInt(color.slice(3, 5), 16);
      var b = parseInt(color.slice(5, 7), 16);
      return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
    }
    return color;
  }

  function baseOptions(type) {
    var colors = themeColors();
    var hasAxes = type === "line" || type === "bar";
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: type === "line" || type === "bar",
          position: "bottom",
          labels: {
            color: colors.text,
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
            padding: 16,
            font: { size: 11, family: "'Plus Jakarta Sans', sans-serif" },
          },
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: "600" },
          bodyFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12 },
          padding: 10,
          cornerRadius: 8,
          displayColors: true,
        },
      },
      scales: hasAxes
        ? {
            x: {
              ticks: { color: colors.muted, font: { size: 10 } },
              grid: { color: soft(colors.border, 0.6), drawBorder: false },
              border: { display: false },
            },
            y: {
              ticks: { color: colors.muted, font: { size: 10 } },
              grid: { color: soft(colors.border, 0.6), drawBorder: false },
              border: { display: false },
              beginAtZero: true,
            },
          }
        : {},
    };
  }

  function merge(a, b) {
    return Object.assign({}, a, b || {});
  }

  UITOP.charts = {
    colors: themeColors,
    soft: soft,

    create: function (canvas, type, data, options) {
      if (!canvas || typeof Chart === "undefined") return null;
      var ctx = canvas.getContext && canvas.getContext("2d");
      if (!ctx) return null;
      return new Chart(ctx, {
        type: type,
        data: data,
        options: merge(baseOptions(type), options),
      });
    },

    createLine: function (canvas, data, options) {
      return UITOP.charts.create(canvas, "line", data, options);
    },

    createBar: function (canvas, data, options) {
      return UITOP.charts.create(canvas, "bar", data, options);
    },

    createDoughnut: function (canvas, data, options) {
      var opts = merge(baseOptions("doughnut"), {
        cutout: "72%",
        plugins: {
          legend: { display: false },
          tooltip: baseOptions("doughnut").plugins.tooltip,
        },
      });
      return UITOP.charts.create(canvas, "doughnut", data, merge(opts, options));
    },

    createSparkline: function (canvas, values, color) {
      if (!canvas || typeof Chart === "undefined") return null;
      var c = color || themeColors().accent;
      return new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
          labels: values.map(function (_, i) { return i; }),
          datasets: [
            {
              data: values,
              borderColor: c,
              backgroundColor: soft(c, 0.15),
              fill: true,
              tension: 0.4,
              borderWidth: 2,
              pointRadius: 0,
              pointHoverRadius: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: { x: { display: false }, y: { display: false } },
          elements: { line: { borderJoinStyle: "round" } },
        },
      });
    },

    createGauge: function (canvas, value, color) {
      if (!canvas || typeof Chart === "undefined") return null;
      var c = color || themeColors().accent;
      var rest = Math.max(0, 100 - value);
      return new Chart(canvas.getContext("2d"), {
        type: "doughnut",
        data: {
          datasets: [
            {
              data: [value, rest],
              backgroundColor: [c, soft(c, 0.12)],
              borderWidth: 0,
              circumference: 240,
              rotation: 240,
            },
          ],
        },
        options: {
          responsive: false,
          cutout: "78%",
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
        },
      });
    },
  };
})();
