/* Codex Council — progressive enhancement: theme toggle, mobile nav, reveal. */
(function () {
  "use strict";

  /* ---- Theme toggle -------------------------------------------------- */
  var root = document.documentElement;
  var italian = root.lang === "it";
  var toggle = document.querySelector("[data-theme-toggle]");

  function currentTheme() {
    return (
      root.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    );
  }

  if (toggle) {
    root.style.colorScheme = currentTheme();
    toggle.setAttribute("aria-label", italian ? "Tema scuro" : "Dark theme");
    toggle.setAttribute("aria-pressed", String(currentTheme() === "dark"));

    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      root.style.colorScheme = next;
      try {
        localStorage.setItem("cc-theme", next);
      } catch (e) {}
      toggle.setAttribute("aria-pressed", String(next === "dark"));
    });
  }

  /* ---- Mobile navigation --------------------------------------------- */
  var nav = document.querySelector(".nav");
  var navToggle = document.querySelector("[data-nav-toggle]");

  if (nav && navToggle) {
    var openMenuLabel = italian ? "Apri menu" : "Open menu";
    var closeMenuLabel = italian ? "Chiudi menu" : "Close menu";
    var close = function () {
      nav.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", openMenuLabel);
    };

    navToggle.addEventListener("click", function () {
      var open = nav.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", String(open));
      navToggle.setAttribute("aria-label", open ? closeMenuLabel : openMenuLabel);
      if (open) {
        requestAnimationFrame(function () {
          nav.querySelector(".nav-links a")?.focus();
        });
      }
    });

    nav.querySelectorAll(".nav-links a").forEach(function (link) {
      link.addEventListener("click", close);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("nav-open")) {
        close();
        navToggle.focus();
      }
    });
  }

  /* ---- ASCII brain banner (loaded once, shared) ---------------------- */
  var brainEl = document.querySelector("[data-brain]");
  if (brainEl) {
    fetch(brainEl.getAttribute("data-brain"))
      .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
      .then(function (t) {
        var lines = t.replace(/\s+$/, "").split("\n");
        var indent = lines.reduce(function (smallest, line) {
          if (!line.trim()) return smallest;
          return Math.min(smallest, line.match(/^\s*/)[0].length);
        }, Infinity);
        if (!Number.isFinite(indent)) indent = 0;
        brainEl.textContent = lines.map(function (line) {
          return line.slice(indent);
        }).join("\n");
      })
      .catch(function () { brainEl.closest(".brain-frame")?.remove(); });
  }

  /* ---- Copy buttons on code / prompt blocks -------------------------- */
  if (navigator.clipboard) {
    var copyText = italian ? "Copia" : "Copy";
    var copiedText = italian ? "Copiato" : "Copied";
    var copyFailedText = italian ? "Errore" : "Failed";

    document.querySelectorAll(
      "pre:not(.brain-art):not(.ascii-art):not([aria-hidden='true']), .prompt"
    ).forEach(function (block, index) {
      var code = block.querySelector("code");
      var copyValue = (code ? code.innerText : block.innerText).trim();
      var container = block.closest("article, section, details, .card");
      var heading = container?.querySelector("h1, h2, h3, summary");
      var context = heading?.textContent.trim().replace(/\s+/g, " ");
      var blockNumber = index + 1;
      var copyLabel = italian
        ? "Copia il blocco " + blockNumber + (context ? " — " + context : "") + " negli appunti"
        : "Copy block " + blockNumber + (context ? " — " + context : "") + " to clipboard";
      var btn = document.createElement("button");
      var status = document.createElement("span");
      btn.type = "button";
      btn.className = "copy-btn";
      btn.textContent = copyText;
      btn.setAttribute("aria-label", copyLabel);
      status.className = "sr-only copy-status";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      status.setAttribute("aria-atomic", "true");
      btn.addEventListener("click", function () {
        status.textContent = "";
        navigator.clipboard.writeText(copyValue).then(function () {
          btn.textContent = copiedText;
          btn.classList.add("copied");
          status.textContent = italian
            ? "Blocco " + blockNumber + " copiato."
            : "Block " + blockNumber + " copied.";
          setTimeout(function () {
            btn.textContent = copyText;
            btn.classList.remove("copied");
          }, 1600);
        }).catch(function () {
          btn.textContent = copyFailedText;
          btn.classList.add("copy-failed");
          status.textContent = italian
            ? "Copia del blocco " + blockNumber + " non riuscita."
            : "Could not copy block " + blockNumber + ".";
          setTimeout(function () {
            btn.textContent = copyText;
            btn.classList.remove("copy-failed");
          }, 1800);
        });
      });
      block.appendChild(btn);
      block.appendChild(status);
    });
  }

  /* ---- Wiki TOC scroll-spy ------------------------------------------- */
  var tocLinks = Array.from(document.querySelectorAll(".wiki-toc a"));
  if (tocLinks.length) {
    var tocSections = tocLinks
      .map(function (link) {
        return document.getElementById(link.getAttribute("href").replace(/^#/, ""));
      })
      .filter(Boolean);
    var tocFrame = 0;

    var updateToc = function () {
      tocFrame = 0;
      var active = tocSections[0];
      var threshold = 128;
      tocSections.forEach(function (section) {
        if (section.getBoundingClientRect().top <= threshold) active = section;
      });
      tocLinks.forEach(function (link) {
        var selected = active && link.getAttribute("href") === "#" + active.id;
        link.classList.toggle("active", Boolean(selected));
        if (selected) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    };

    var scheduleToc = function () {
      if (!tocFrame) tocFrame = requestAnimationFrame(updateToc);
    };

    updateToc();
    window.addEventListener("scroll", scheduleToc, { passive: true });
    window.addEventListener("resize", scheduleToc);
  }

  /* ---- Keyboard access for horizontally scrollable regions ---------- */
  var scrollLabel = root.lang === "it" ? "Contenuto scorrevole" : "Scrollable content";
  var scrollRegions = Array.from(document.querySelectorAll(
    ".wiki-toc, .table-wrap, .forge-stage, .brain-frame, .ascii-frame, pre:not(.brain-art):not(.ascii-art)"
  ));

  var updateScrollableRegions = function () {
    scrollRegions.forEach(function (region) {
      var overflows = region.scrollWidth > region.clientWidth + 1;
      if (overflows) {
        if (!region.hasAttribute("tabindex")) {
          region.dataset.autoScrollable = "true";
        }
        region.setAttribute("tabindex", "0");
        if (!region.hasAttribute("aria-label")) {
          region.dataset.autoScrollLabel = "true";
          region.setAttribute("aria-label", scrollLabel);
        }
      } else {
        if (region.dataset.autoScrollable === "true") {
          region.removeAttribute("tabindex");
          delete region.dataset.autoScrollable;
        }
        if (region.dataset.autoScrollLabel === "true") {
          region.removeAttribute("aria-label");
          delete region.dataset.autoScrollLabel;
        }
      }
    });
  };

  requestAnimationFrame(updateScrollableRegions);
  window.addEventListener("resize", updateScrollableRegions);
  if ("ResizeObserver" in window) {
    var scrollObserver = new ResizeObserver(updateScrollableRegions);
    scrollRegions.forEach(function (region) { scrollObserver.observe(region); });
  }

  /* ---- Reveal on scroll ---------------------------------------------- */
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var targets = document.querySelectorAll(
    ".card, .metric, .step, .panel, .visual-frame, .wide-list li, .callout, .table-wrap, .feature-copy, .hero-trust, .home-signal, .workflow-card, .proof-item, .home-close-shell"
  );

  if (reduce || !("IntersectionObserver" in window)) {
    return; // leave content fully visible
  }

  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.05 }
  );

  targets.forEach(function (el, i) {
    var rect = el.getBoundingClientRect();
    // Already in view at load: show immediately, no flash.
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      el.classList.add("is-visible");
      return;
    }
    el.classList.add("reveal");
    el.style.transitionDelay = (i % 4) * 60 + "ms";
    io.observe(el);
  });
})();
