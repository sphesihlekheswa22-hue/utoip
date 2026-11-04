(function () {
  "use strict";

  /* ═══════════════════════════════════════════════════════════
     UITOP Auth Login — Premium Edition
     Canvas particles, stat counters, enhanced interactions
     ═══════════════════════════════════════════════════════════ */

  const form = document.getElementById("login-form");
  const toggle = document.getElementById("toggle-password");
  const password = document.getElementById("password");
  const submit = document.getElementById("login-submit");

  /* ── Password Toggle ── */
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
      // Focus back to password for continuity
      password.focus();
    });
  }

  /* ── Form Submit with Loading State ── */
  if (form && submit) {
    form.addEventListener("submit", function (e) {
      const email = document.getElementById("email");
      if (!email?.value || !password?.value) return;

      submit.disabled = true;
      const label = submit.querySelector(".login-submit-label");
      const busy = submit.querySelector(".login-submit-busy");
      if (label) label.hidden = true;
      if (busy) busy.hidden = false;

      // Add a subtle pulse to the card while loading
      const card = document.querySelector(".login-card");
      if (card) {
        card.style.transition = "box-shadow 0.6s ease";
        card.style.boxShadow = "0 24px 64px -28px rgba(11, 58, 110, 0.35), 0 0 0 1px rgba(26, 95, 168, 0.1)";
      }
    });
  }

  /* ── Dynamic Year ── */
  const year = document.getElementById("uitop-year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* ── Stat Counter Animation ── */
  function animateCounters() {
    const counters = document.querySelectorAll(".auth-stat-value");
    counters.forEach(counter => {
      const target = parseFloat(counter.getAttribute("data-count"));
      const isFloat = target % 1 !== 0;
      const duration = 2000;
      const startTime = performance.now();
      const suffix = target === 99.9 ? "%" : "";
      if (suffix) counter.setAttribute("data-suffix", suffix);

      function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out expo
        const eased = 1 - Math.pow(1 - progress, 4);
        const current = target * eased;

        if (isFloat) {
          counter.textContent = current.toFixed(1);
        } else {
          counter.textContent = Math.floor(current).toLocaleString();
        }

        if (progress < 1) {
          requestAnimationFrame(update);
        } else {
          if (isFloat) {
            counter.textContent = target.toFixed(1);
          } else {
            counter.textContent = target.toLocaleString();
          }
        }
      }

      requestAnimationFrame(update);
    });
  }

  // Start counters after a brief delay for dramatic effect
  setTimeout(animateCounters, 600);

  /* ═══════════════════════════════════════════════════════════
     CANVAS PARTICLE SYSTEM — Floating Data Nodes
     ═══════════════════════════════════════════════════════════ */

  const canvas = document.getElementById("brand-canvas");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    let particles = [];
    let animationId;
    let mouseX = 0;
    let mouseY = 0;
    let isActive = true;

    function resizeCanvas() {
      const parent = canvas.parentElement;
      if (!parent) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = parent.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      ctx.scale(dpr, dpr);
    }

    class Particle {
      constructor(w, h) {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.radius = Math.random() * 2 + 0.5;
        this.opacity = Math.random() * 0.4 + 0.1;
        this.pulse = Math.random() * Math.PI * 2;
        this.pulseSpeed = Math.random() * 0.02 + 0.01;
        this.color = Math.random() > 0.5 
          ? "47, 158, 68"   // green
          : "26, 95, 168";  // blue
      }

      update(w, h) {
        this.x += this.vx;
        this.y += this.vy;
        this.pulse += this.pulseSpeed;

        // Wrap around
        if (this.x < -10) this.x = w + 10;
        if (this.x > w + 10) this.x = -10;
        if (this.y < -10) this.y = h + 10;
        if (this.y > h + 10) this.y = -10;

        // Subtle mouse influence
        const dx = this.x - mouseX;
        const dy = this.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          const force = (150 - dist) / 150 * 0.02;
          this.vx += dx * force * 0.01;
          this.vy += dy * force * 0.01;
        }

        // Damping
        this.vx *= 0.999;
        this.vy *= 0.999;
      }

      draw(ctx) {
        const pulseOpacity = this.opacity + Math.sin(this.pulse) * 0.15;
        const actualOpacity = Math.max(0.05, Math.min(0.5, pulseOpacity));

        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${this.color}, ${actualOpacity})`;
        ctx.fill();

        // Glow for larger particles
        if (this.radius > 1.8) {
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius * 3, 0, Math.PI * 2);
          const gradient = ctx.createRadialGradient(
            this.x, this.y, 0,
            this.x, this.y, this.radius * 3
          );
          gradient.addColorStop(0, `rgba(${this.color}, ${actualOpacity * 0.3})`);
          gradient.addColorStop(1, `rgba(${this.color}, 0)`);
          ctx.fillStyle = gradient;
          ctx.fill();
        }
      }
    }

    function initParticles() {
      const rect = canvas.parentElement.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const count = Math.min(Math.floor((w * h) / 8000), 80);
      particles = [];
      for (let i = 0; i < count; i++) {
        particles.push(new Particle(w, h));
      }
    }

    function drawConnections(w, h) {
      const maxDist = 120;
      const maxConnections = 3;

      for (let i = 0; i < particles.length; i++) {
        let connections = 0;
        for (let j = i + 1; j < particles.length && connections < maxConnections; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < maxDist) {
            const opacity = (1 - dist / maxDist) * 0.12;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
            connections++;
          }
        }
      }
    }

    function animate() {
      if (!isActive) return;

      const rect = canvas.parentElement.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      ctx.clearRect(0, 0, w, h);

      particles.forEach(p => {
        p.update(w, h);
        p.draw(ctx);
      });

      drawConnections(w, h);
      animationId = requestAnimationFrame(animate);
    }

    // Mouse tracking for interactivity
    canvas.parentElement.addEventListener("mousemove", (e) => {
      const rect = canvas.parentElement.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    });

    // Visibility handling
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        isActive = false;
        if (animationId) cancelAnimationFrame(animationId);
      } else {
        isActive = true;
        animate();
      }
    });

    // Initialize
    resizeCanvas();
    initParticles();
    animate();

    window.addEventListener("resize", () => {
      resizeCanvas();
      initParticles();
    });
  }

  /* ── Demo Fill Buttons with Ripple Effect ── */
  document.querySelectorAll(".login-demo-fill").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      const email = document.getElementById("email");
      const password = document.getElementById("password");
      if (email) {
        email.value = btn.getAttribute("data-email") || "";
        email.focus();
      }
      if (password) password.value = btn.getAttribute("data-password") || "";

      // Ripple effect
      const ripple = document.createElement("span");
      ripple.style.cssText = `
        position: absolute;
        border-radius: 50%;
        background: rgba(26, 95, 168, 0.15);
        transform: scale(0);
        animation: ripple-effect 0.5s ease-out;
        pointer-events: none;
      `;
      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + "px";
      ripple.style.left = (e.clientX - rect.left - size / 2) + "px";
      ripple.style.top = (e.clientY - rect.top - size / 2) + "px";
      btn.style.position = "relative";
      btn.style.overflow = "hidden";
      btn.appendChild(ripple);
      setTimeout(() => ripple.remove(), 500);
    });
  });

  // Add ripple keyframes dynamically
  if (!document.getElementById("ripple-style")) {
    const style = document.createElement("style");
    style.id = "ripple-style";
    style.textContent = `
      @keyframes ripple-effect {
        to { transform: scale(4); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  /* ── Input Focus Enhancements ── */
  document.querySelectorAll(".login-input input").forEach(input => {
    input.addEventListener("focus", function() {
      const parent = this.closest(".login-field");
      if (parent) parent.classList.add("is-focused");
    });
    input.addEventListener("blur", function() {
      const parent = this.closest(".login-field");
      if (parent) parent.classList.remove("is-focused");
    });
  });

  /* ── Smooth Alert Dismiss (if needed later) ── */
  document.querySelectorAll(".login-alert").forEach(alert => {
    alert.style.cursor = "default";
  });

})();