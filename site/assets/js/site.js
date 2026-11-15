// Progressive enhancement for every page of the site and of the lab
// application. Content never depends on it. It is loaded in the head
// without defer, so that the sidebar's state applies before the first
// paint; the rest waits until the page is parsed.
//
// - Marks the root element with data-sidebar, "collapsed" or
//   "expanded", as the browser's local storage last kept it for this
//   host, so that the stylesheet shows the sidebar's toggle and the
//   sidebar in that state. Each [data-sidebar-toggle] button flips the
//   state, keeps it and reports it in aria-expanded; a change made in
//   another window of the host applies here too.
// - Reveals each [data-print] button and makes it open the print dialog.
// - Reveals each [data-copy-smiles] button. It copies the SMILES string of
//   the [data-smiles] element beside it with the Clipboard API, and selects
//   that text instead when the API is missing or refuses (plain-http hosts).
//   It reports either outcome in the page's language, from its
//   data-copied and data-selected attributes.
// - On http: and https: pages, replaces the text of each span.page-url
//   with location.href, so a browser printout shows the address in use.
(() => {
  "use strict";

  const SIDEBAR = "orgsyndb-sidebar";
  const root = document.documentElement;

  const showSidebar = (expanded) => {
    root.dataset.sidebar = expanded ? "expanded" : "collapsed";
    for (const button of document.querySelectorAll("[data-sidebar-toggle]")) {
      button.setAttribute("aria-expanded", String(expanded));
    }
  };

  const storedSidebar = () => {
    try {
      return window.localStorage.getItem(SIDEBAR);
    } catch {
      return null;
    }
  };

  showSidebar(storedSidebar() !== "collapsed");
  window.addEventListener("storage", (event) => {
    if (event.key === SIDEBAR) showSidebar(event.newValue !== "collapsed");
  });

  const flash = (button, text) => {
    const label = button.dataset.label || button.textContent;
    button.dataset.label = label;
    button.textContent = text;
    window.clearTimeout(Number(button.dataset.timer || 0));
    button.dataset.timer = String(window.setTimeout(() => {
      button.textContent = label;
    }, 2500));
  };

  const selectText = (element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  };

  const enhance = () => {
    showSidebar(root.dataset.sidebar !== "collapsed");
    for (const button of document.querySelectorAll("[data-sidebar-toggle]")) {
      button.addEventListener("click", () => {
        const expanded = root.dataset.sidebar === "collapsed";
        showSidebar(expanded);
        try {
          window.localStorage.setItem(
            SIDEBAR, expanded ? "expanded" : "collapsed");
        } catch {
          // Without storage the state holds until the page is left.
        }
      });
    }

    for (const button of document.querySelectorAll("[data-print]")) {
      button.addEventListener("click", () => window.print());
      button.hidden = false;
    }

    for (const button of document.querySelectorAll("[data-copy-smiles]")) {
      const code = button.parentElement.querySelector("[data-smiles]");
      if (!code) continue;
      button.addEventListener("click", async () => {
        const text = code.textContent.trim();
        try {
          if (!navigator.clipboard || !window.isSecureContext) {
            throw new Error("Clipboard API unavailable");
          }
          await navigator.clipboard.writeText(text);
          flash(button, button.dataset.copied || "Copied");
        } catch {
          selectText(code);
          flash(button, button.dataset.selected || "Selected: press Ctrl+C");
        }
      });
      button.hidden = false;
    }

    if (location.protocol === "http:" || location.protocol === "https:") {
      for (const span of document.querySelectorAll("span.page-url")) {
        span.textContent = location.href;
      }
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhance);
  } else {
    enhance();
  }
})();
