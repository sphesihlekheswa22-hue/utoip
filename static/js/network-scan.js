/**
 * Shared LAN discovery client for Computers / Network / Servers / Printers scan pages.
 */
(function (global) {
  "use strict";

  function toast(msg, kind) {
    if (global.UITOP && UITOP.utils && UITOP.utils.toast) {
      UITOP.utils.toast(msg, kind || "info");
    }
  }

  function emptyTotals() {
    return {
      devices: 0,
      computers: 0,
      printers: 0,
      network: 0,
      routers: 0,
      switches: 0,
      firewalls: 0,
      unknown: 0,
      servers: 0,
      discovered: 0,
      managed: 0,
      unmanaged: 0,
      offline: 0,
      sources: 1,
    };
  }

  /**
   * @param {object} opts
   * @param {string} [opts.filter] — computers|servers|printers|network|all
   * @param {string} [opts.preferType] — type used when importing
   * @param {string} [opts.readyText]
   * @param {function} [opts.mapResults] — (hosts) => rows for the page
   * @param {function} [opts.mapTotals] — (totals, hosts) => totals object for the page
   */
  function createScanner(opts) {
    opts = opts || {};
    return {
      scanning: false,
      done: false,
      progress: 0,
      statusText: opts.readyText || "Select a private /24 subnet and start discovery.",
      cidr: "",
      suggested: [],
      totals: emptyTotals(),
      t: emptyTotals(),
      results: [],
      jobId: null,
      _pollTimer: null,

      async init() {
        try {
          var res = await fetch("/discovery/suggest", { credentials: "same-origin" });
          if (!res.ok) return;
          var data = await res.json();
          this.suggested = data.cidrs || [];
          if (!this.cidr && this.suggested.length) this.cidr = this.suggested[0];
        } catch (e) {
          /* ignore — user can type CIDR */
        }
      },

      startScan() {
        return this.start();
      },

      async start() {
        if (this.scanning) return;
        var cidr = (this.cidr || "").trim();
        if (!cidr) {
          toast("Enter a subnet CIDR (e.g. 192.168.1.0/24)", "error");
          return;
        }
        this.scanning = true;
        this.done = false;
        this.progress = 0;
        this.results = [];
        this.totals = emptyTotals();
        this.t = emptyTotals();
        this.statusText = "Starting scan of " + cidr + "…";
        this._clearPoll();

        try {
          var res = await fetch("/discovery/scan", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ cidr: cidr, filter: opts.filter || null }),
          });
          var data = await res.json().catch(function () {
            return {};
          });
          if (!res.ok) {
            throw new Error(data.error || "Failed to start scan");
          }
          this.jobId = data.job_id;
          this.statusText = "Scanning " + (data.cidr || cidr) + "…";
          this._poll();
        } catch (err) {
          this.scanning = false;
          this.statusText = err.message || "Scan failed to start";
          toast(this.statusText, "error");
        }
      },

      _clearPoll() {
        if (this._pollTimer) {
          clearTimeout(this._pollTimer);
          this._pollTimer = null;
        }
      },

      _poll() {
        var self = this;
        if (!this.jobId) return;
        fetch("/discovery/scan/" + encodeURIComponent(this.jobId), {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (pack) {
            if (!pack.ok) throw new Error(pack.data.error || "Scan status failed");
            var job = pack.data;
            self.progress = job.progress || 0;
            self.statusText = job.status_text || self.statusText;
            if (job.status === "running") {
              self._pollTimer = setTimeout(function () {
                self._poll();
              }, 600);
              return;
            }
            self.scanning = false;
            self.done = job.status === "done";
            if (job.status === "error") {
              toast(job.error || "Scan failed", "error");
              return;
            }
            var hosts = job.hosts || [];
            var totals = Object.assign(emptyTotals(), job.totals || {});
            self.totals = opts.mapTotals ? opts.mapTotals(totals, hosts) : totals;
            self.t = self.totals;
            self.results = opts.mapResults ? opts.mapResults(hosts) : hosts;
            toast("Found " + hosts.length + " host(s)", "success");
          })
          .catch(function (err) {
            self.scanning = false;
            self.statusText = err.message || "Scan failed";
            toast(self.statusText, "error");
          });
      },

      async importHost(r) {
        try {
          var res = await fetch("/discovery/import", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({
              prefer_type: opts.preferType || r.type || null,
              hosts: [r],
            }),
          });
          var data = await res.json().catch(function () {
            return {};
          });
          if (!res.ok) throw new Error(data.error || "Import failed");
          if (data.created_count) {
            r.managed = true;
            r.agent = r.agent || "Agent Missing";
            if (this.totals) {
              this.totals.managed = (this.totals.managed || 0) + 1;
              this.totals.unmanaged = Math.max(0, (this.totals.unmanaged || 0) - 1);
            }
            if (this.t) {
              this.t.managed = (this.t.managed || 0) + 1;
              this.t.unmanaged = Math.max(0, (this.t.unmanaged || 0) - 1);
            }
            toast("Imported " + (r.hostname || r.name || r.ip), "success");
          } else {
            r.managed = true;
            toast((r.hostname || r.ip) + " already in inventory", "info");
          }
        } catch (err) {
          toast(err.message || "Import failed", "error");
        }
      },

      deploy(r) {
        return this.importHost(r);
      },

      enroll(r) {
        return this.importHost(r);
      },

      assignSnmp(r) {
        return this.importHost(Object.assign({}, r, { type: r.type || "Network" }));
      },

      copyLink(r) {
        var host = r.hostname || r.name || r.ip;
        var link =
          (global.location && global.location.origin ? global.location.origin : "") +
          "/computers/install-agent?host=" +
          encodeURIComponent(host);
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(link);
          toast("Installation link copied", "success");
        }
      },
    };
  }

  global.UITOP = global.UITOP || {};
  global.UITOP.createNetworkScanner = createScanner;
})(window);
