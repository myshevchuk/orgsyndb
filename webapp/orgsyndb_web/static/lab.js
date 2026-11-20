// The lab application's script, loaded on every page of the shell
// after htmx. What it wires today lives on the item list, where the
// browser opens and closes popups by itself and the view controls
// take effect through lab.css; the script adds:
//
// - Places each popup below the button that opened it, or above it
//   when there is no room below, or else over it, always inside the
//   window, and keeps it there while the page or a table box scrolls.
// - Submits the form of a control marked data-submit when its value
//   changes, and hides that form's submit buttons.
// - Restores each control marked data-remember from localStorage when
//   the page loads, and saves it there whenever it changes.
// - Checks the item list's switch `Details` (#detail-switch) and saves
//   it when the address holds `detail`. Turning the switch on writes
//   the id of the marked row into the address as `detail`; turning it
//   off removes `detail`.
// - While the switch is checked, chooses a row: a plain click in it,
//   on a link too but not on a check box, or an arrow key up or down
//   in the table, which also focuses the row it moves to. Choosing
//   fires the event `item-select` on the row, which makes htmx load the
//   row's details into #item-detail, and nothing else.
// - Once htmx has swapped details in, marks the row that asked for them
//   with aria-current="true" and writes its id into the address as
//   `detail`. A request that is aborted or fails swaps nothing, so
//   pane, mark and address stay as they were. While details load, the
//   pane is inert.
//
// OrgSynLab.place is the placement's arithmetic and
// OrgSynLab.detailSearch the address's, each kept apart from the page
// so that tests can run it without one.
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

  // The query string of SEARCH, as location.search holds it, with or
  // without its leading "?", whose parameter `detail` is set to ID, a
  // number or text, or removed when ID is null; every other parameter
  // keeps its text and its place. It is "?" and the parameters, or ""
  // when none is left. Repeated `detail` parameters become one, at the
  // place of the first.
  const detailSearch = (search, id) => {
    const kept = [];
    let placed = id === null || id === undefined;
    for (const pair of search.replace(/^\?/, "").split("&")) {
      if (pair === "") continue;
      if (pair.split("=", 1)[0] !== "detail") {
        kept.push(pair);
      } else if (!placed) {
        kept.push(`detail=${encodeURIComponent(id)}`);
        placed = true;
      }
    }
    if (!placed) kept.push(`detail=${encodeURIComponent(id)}`);
    return kept.length ? `?${kept.join("&")}` : "";
  };

  globalThis.OrgSynLab = { place, detailSearch };
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

  const detailSwitch = document.getElementById("detail-switch");
  if (!detailSwitch) return;
  const ROWS = ".item-table tbody tr[data-item]";

  const markedRow = () => document.querySelector(
    `${ROWS}[aria-current="true"]`);

  const writeDetail = (id) => {
    try {
      history.replaceState(
        history.state, "",
        `${location.pathname}${detailSearch(location.search, id)}`
        + location.hash);
    } catch {
      // The address cannot change: the page shows the item regardless.
    }
  };

  // Rows take focus only while the details show, so that the arrow
  // keys have a row to start from.
  const focusable = () => {
    for (const row of document.querySelectorAll(ROWS)) {
      if (detailSwitch.checked) {
        row.tabIndex = -1;
      } else {
        row.removeAttribute("tabindex");
      }
    }
  };

  detailSwitch.addEventListener("change", () => {
    const row = markedRow();
    writeDetail(detailSwitch.checked && row ? row.dataset.item : null);
    focusable();
  });

  // A shared address holding `detail` opens on the item, whatever the
  // reader's stored choice; a switch restored as checked names the
  // marked row in the address.
  if (/(^|[?&])detail(=|&|$)/.test(location.search)) {
    detailSwitch.checked = true;
    detailSwitch.dispatchEvent(new Event("change"));
  } else if (detailSwitch.checked) {
    const row = markedRow();
    writeDetail(row ? row.dataset.item : null);
  }
  focusable();

  // While a row's details load, the pane takes neither pointer nor
  // keyboard, so the previous item's links cannot be used; it is
  // usable again once the request ends without swapping.
  document.addEventListener("htmx:beforeRequest", (event) => {
    const pane = document.getElementById("item-detail");
    if (pane && event.target.matches && event.target.matches(ROWS)) {
      pane.inert = true;
    }
  });
  document.addEventListener("htmx:afterRequest", (event) => {
    const pane = document.getElementById("item-detail");
    if (pane && event.target.matches && event.target.matches(ROWS)) {
      pane.inert = pane.classList.contains("htmx-request");
    }
  });

  // Asks htmx for the details of ROW.
  const choose = (row) => htmx.trigger(row, "item-select");

  document.addEventListener("click", (event) => {
    if (!detailSwitch.checked || typeof htmx === "undefined") return;
    if (event.button !== 0 || event.ctrlKey || event.metaKey
        || event.shiftKey || event.altKey) {
      return;
    }
    if (!(event.target instanceof Element)) return;
    const row = event.target.closest(ROWS);
    if (!row || event.target.closest("input")) return;
    event.preventDefault();
    choose(row);
  });

  document.addEventListener("keydown", (event) => {
    if (!detailSwitch.checked || typeof htmx === "undefined") return;
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
      return;
    }
    if (!(event.target instanceof Element)
        || !event.target.closest(".item-table")) {
      return;
    }
    const from = event.target.closest(ROWS) || markedRow();
    if (!from) return;
    event.preventDefault();
    const rows = [...document.querySelectorAll(ROWS)];
    const step = event.key === "ArrowDown" ? 1 : -1;
    const to = rows[rows.indexOf(from) + step];
    if (!to) return;
    to.focus();
    choose(to);
  });

  // htmx dispatches htmx:afterSwap on the elements it swapped in, and
  // names the element that asked for them in the request's
  // configuration.
  document.addEventListener("htmx:afterSwap", (event) => {
    const row = event.detail.requestConfig
      && event.detail.requestConfig.elt;
    if (!row || !row.matches || !row.matches(ROWS)) return;
    for (const old of document.querySelectorAll(ROWS)) {
      old.removeAttribute("aria-current");
    }
    row.setAttribute("aria-current", "true");
    if (detailSwitch.checked) writeDetail(row.dataset.item);
  });
})();
