/* Codex Council — progressive enhancement: theme toggle, mobile nav, reveal. */
(function () {
  "use strict";

  /* ---- Theme toggle -------------------------------------------------- */
  var root = document.documentElement;
  var toggle = document.querySelector("[data-theme-toggle]");

  function currentTheme() {
    return (
      root.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    );
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
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
    var close = function () {
      nav.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
    };

    navToggle.addEventListener("click", function () {
      var open = nav.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", String(open));
    });

    nav.querySelectorAll(".nav-links a").forEach(function (link) {
      link.addEventListener("click", close);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });
  }

  /* ---- ASCII brain banner (loaded once, shared) ---------------------- */
  var brainEl = document.querySelector("[data-brain]");
  if (brainEl) {
    fetch(brainEl.getAttribute("data-brain"))
      .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
      .then(function (t) { brainEl.textContent = t.replace(/\s+$/, ""); })
      .catch(function () { brainEl.closest(".brain-frame")?.remove(); });
  }

  /* ---- Copy buttons on code / prompt blocks -------------------------- */
  if (navigator.clipboard) {
    document.querySelectorAll("pre:not(.brain-art), .prompt").forEach(function (block) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "copy-btn";
      btn.textContent = "Copy";
      btn.setAttribute("aria-label", "Copy to clipboard");
      btn.addEventListener("click", function () {
        var code = block.querySelector("code") || block;
        navigator.clipboard.writeText(code.innerText.trim()).then(function () {
          btn.textContent = "Copied";
          btn.classList.add("copied");
          setTimeout(function () {
            btn.textContent = "Copy";
            btn.classList.remove("copied");
          }, 1600);
        });
      });
      block.appendChild(btn);
    });
  }

  /* ---- Wiki TOC scroll-spy ------------------------------------------- */
  var tocLinks = document.querySelectorAll(".wiki-toc a");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var byId = {};
    tocLinks.forEach(function (a) {
      byId[a.getAttribute("href").replace(/^#/, "")] = a;
    });
    var spy = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            tocLinks.forEach(function (a) { a.classList.remove("active"); });
            var link = byId[entry.target.id];
            if (link) link.classList.add("active");
          }
        });
      },
      { rootMargin: "-80px 0px -70% 0px", threshold: 0 }
    );
    document.querySelectorAll(".wiki-content > section[id]").forEach(function (s) {
      spy.observe(s);
    });
  }

  /* ---- Reveal on scroll ---------------------------------------------- */
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var targets = document.querySelectorAll(
    ".card, .metric, .step, .panel, .visual-frame, .wide-list li, .callout, .table-wrap, .feature-copy, .hero-trust"
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
