// Progressive enhancement for every page. Content never depends on it.
//
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
})();
