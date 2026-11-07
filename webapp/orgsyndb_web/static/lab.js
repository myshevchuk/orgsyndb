// Progressive enhancement for the lab's item list. The page works
// without it: the browser opens and closes popups by itself, and the
// view controls take effect through lab.css.
//
// - Places each popup below the button that opened it, or above it
//   when there is no room below, or else over it, always inside the
//   window, and keeps it there while the page or a table box scrolls.
// - Submits the form of a control marked data-submit when its value
//   changes, and hides that form's submit buttons.
// - Restores each control marked data-remember from localStorage when
//   the page loads, and saves it there whenever it changes.
//
// OrgSynLab.place is the placement's arithmetic, kept apart from the
// page so that tests can run it without one.
(() => {
  "use strict";

  const GAP = 8;
  const EDGE = 16;

  // The left and top of a popup of SIZE (width, height) beside ANCHOR
  // (left, top, right, bottom), in a window of VIEW (width, height):
  // below the anchor from its left edge, or above it when the popup
  // does not fit below but does above, or else as low as the window
  // allows, over the anchor; always kept EDGE pixels inside the
  // window's edges, its top first when it is taller than the window.
  const place = (anchor, size, view) => {
    const left = Math.max(EDGE, Math.min(anchor.left,
                                         view.width - size.width - EDGE));
    const below = anchor.bottom + GAP;
    const above = anchor.top - GAP - size.height;
    const lowest = Math.max(EDGE, view.height - size.height - EDGE);
    if (below <= lowest) return { left, top: below };
    return { left, top: above >= EDGE ? above : lowest };
  };

  globalThis.OrgSynLab = { place };
  if (typeof document === "undefined") return;

  let open = null;

  const opener = (popup) => [
    ...document.querySelectorAll("[popovertarget]"),
  ].find((button) => button.getAttribute("popovertarget") === popup.id
         && !popup.contains(button));

  const reposition = () => {
    if (!open) return;
    const button = opener(open);
    if (!button) return;
    const spot = place(button.getBoundingClientRect(),
                       { width: open.offsetWidth, height: open.offsetHeight },
                       { width: document.documentElement.clientWidth,
                         height: window.innerHeight });
    open.style.left = `${spot.left}px`;
    open.style.top = `${spot.top}px`;
  };

  document.addEventListener("toggle", (event) => {
    const popup = event.target;
    if (!(popup instanceof HTMLElement) || !popup.hasAttribute("popover")) {
      return;
    }
    if (event.newState === "open") {
      open = popup;
      popup.dataset.placed = "";
      reposition();
    } else if (open === popup) {
      open = null;
    }
  }, true);
  document.addEventListener("scroll", reposition, true);
  window.addEventListener("resize", reposition);

  for (const control of document.querySelectorAll("[data-submit]")) {
    const form = control.form;
    if (!form) continue;
    control.addEventListener("change", () => form.requestSubmit());
    for (const button of form.querySelectorAll("button[type=submit]")) {
      button.hidden = true;
    }
  }

  const storage = (() => {
    try {
      return window.localStorage;
    } catch {
      return null;
    }
  })();
  for (const control of document.querySelectorAll("[data-remember]")) {
    const key = `orgsyndb:${control.dataset.remember}`;
    const checkable = control.type === "checkbox";
    let saved = null;
    try {
      saved = storage && storage.getItem(key);
    } catch {
      saved = null;
    }
    if (saved !== null) {
      if (checkable) {
        control.checked = saved === "1";
      } else if ([...control.options].some((o) => o.value === saved)) {
        control.value = saved;
      }
    }
    control.addEventListener("change", () => {
      try {
        if (storage) {
          storage.setItem(key, checkable ? (control.checked ? "1" : "0")
                                         : control.value);
        }
      } catch {
        // Storage refused: the choice lasts until the page is left.
      }
    });
  }
})();
