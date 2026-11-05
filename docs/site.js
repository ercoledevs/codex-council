/* The handbook remains navigable offline and without JavaScript. */
(() => {
  "use strict";
  const root = document.documentElement;
  const it = root.lang === "it";
  const theme = document.querySelector("[data-theme-toggle]");
  theme.hidden = false;
  function setTheme(value) {
    root.dataset.theme = value;
    theme.setAttribute("aria-pressed", String(value === "dark"));
  }
  setTheme(root.dataset.theme || "dark");
  theme.addEventListener("click", () => {
    setTheme(root.dataset.theme === "dark" ? "light" : "dark");
    try { localStorage.setItem("cc-theme", root.dataset.theme); } catch {}
  });

  const nav = document.querySelector(".guide-nav");
  const mobile = matchMedia("(max-width: 720px)");
  const resize = () => { nav.open = !mobile.matches; };
  resize();
  mobile.addEventListener("change", resize);
  const field = nav.querySelector("input");
  const groups = nav.querySelectorAll(".guide-group");
  const status = nav.querySelector("[role=status]");
  field.parentElement.hidden = false;
  function filter() {
    const query = field.value.trim().toLocaleLowerCase();
    let count = 0;
    groups.forEach(group => {
      const links = Array.from(group.querySelectorAll("a"));
      links.forEach(link => {
        const title = link.textContent + " " + link.getAttribute("href");
        link.hidden = !title.toLocaleLowerCase().includes(query);
        if (!link.hidden) count++;
      });
      group.hidden = links.every(link => link.hidden);
    });
    status.textContent = query ? (it ? "Guide trovate: " : "Matching guides: ") + count : "";
  }
  field.addEventListener("input", filter);
  nav.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    if (field.value) {
      field.value = "";
      filter();
      field.focus();
    } else if (mobile.matches) {
      nav.open = false;
      nav.querySelector("summary").focus();
    }
  });

  if (navigator.clipboard) {
    document.querySelectorAll("pre:has(code):not(.ascii-art), .prompt:has(code)").forEach(block => {
      const code = block.querySelector("code");
      const button = document.createElement("button");
      const announcement = document.createElement("span");
      const label = it ? "Copia" : "Copy";
      const context = block.closest("article,section,details")?.querySelector("h3,h2,h1,summary");
      button.type = "button";
      button.className = "copy-btn";
      button.textContent = label;
      button.setAttribute("aria-label", label + (context ? " · " + context.textContent : ""));
      announcement.className = "sr-only";
      announcement.setAttribute("role", "status");
      button.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(code.textContent.trim());
          announcement.textContent = it ? "Copiato" : "Copied";
        } catch {
          announcement.textContent = it ? "Copia non riuscita" : "Copy failed";
        }
        button.textContent = announcement.textContent;
        setTimeout(() => { button.textContent = label; }, 1600);
      });
      block.append(button, announcement);
    });
  }
  const regions = document.querySelectorAll(".table-wrap,.forge-stage,pre");
  const checkScroll = el => {
    if (el.scrollWidth > el.clientWidth + 1) {
      el.tabIndex = 0;
      el.setAttribute("aria-label", it ? "Contenuto scorrevole" : "Scrollable content");
    } else {
      el.removeAttribute("tabindex");
      el.removeAttribute("aria-label");
    }
  };
  const observer = window.ResizeObserver && new ResizeObserver(entries => {
    entries.forEach(entry => checkScroll(entry.target));
  });
  regions.forEach(el => { checkScroll(el); if (observer) observer.observe(el); });
})();
