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
// - Opens the form that a link marked data-dialog leads to in the
//   dialog of the page shell (#lab-dialog) on a plain click, and
//   closes the dialog on a click on its close button or on the form's
//   cancel link; Escape closes it by itself. Closing empties it. A
//   form that is saved there fires the event `lab-saved`; the script
//   then fetches the page again as a page, replaces each element
//   marked data-refresh, and the messages, with the new page's, keeps
//   what the user ticked and chose in the list, closes the dialog and
//   moves focus to where the user was working. The dialog's buttons
//   stay disabled until then. If the page cannot be fetched, the page
//   is reloaded.
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
    if (!control.form) continue;
    for (const button of control.form.querySelectorAll(
      "button[type=submit]")) {
      button.hidden = true;
    }
  }
  // Delegated, so that a control a refresh put in still submits.
  document.addEventListener("change", (event) => {
    const control = event.target;
    if (control instanceof Element && control.matches("[data-submit]")
        && control.form) {
      control.form.requestSubmit();
    }
  });

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
    if (!detailSwitch) return;
    for (const row of document.querySelectorAll(ROWS)) {
      if (detailSwitch.checked) {
        row.tabIndex = -1;
      } else {
        row.removeAttribute("tabindex");
      }
    }
  };

  // The dialog of the page shell, and what the script knows of the
  // form in it.
  const dialog = document.getElementById("lab-dialog");
  const dialogBody = document.getElementById("lab-dialog-body");
  let dialogOpener = null; // the link that opened the dialog
  let loading = null; // the address of the form being requested
  let saving = false; // a save is posted and its refresh not done

  const lockDialog = (locked) => {
    saving = locked;
    for (const button of dialog.querySelectorAll("button")) {
      button.disabled = locked;
    }
  };

  const plain = (event) => event.button === 0 && !event.ctrlKey
    && !event.metaKey && !event.shiftKey && !event.altKey;

  // Replaces every element of the page marked data-refresh, and the
  // messages, with the same element of FRESH, the parsed new page,
  // and returns the elements put in. An element the new page lacks is
  // removed.
  const refreshParts = (fresh) => {
    const added = [];
    for (const old of document.querySelectorAll("[data-refresh][id]")) {
      const next = fresh.getElementById(old.id);
      if (next) {
        const node = document.adoptNode(next);
        old.replaceWith(node);
        added.push(node);
      } else {
        old.remove();
      }
    }
    const shown = document.querySelector("ul.lab-messages");
    const message = fresh.querySelector("ul.lab-messages");
    if (message) {
      const node = document.adoptNode(message);
      if (shown) {
        shown.replaceWith(node);
      } else {
        const main = document.getElementById("main");
        const demo = main.querySelector(":scope > .lab-demo");
        if (demo) {
          demo.after(node);
        } else {
          main.prepend(node);
        }
      }
    } else if (shown) {
      shown.remove();
    }
    document.title = fresh.title;
    return added;
  };

  // Brings what the user set in the item list back after its parts
  // were replaced: TICKED, the values of the check boxes that were
  // ticked, the rows' focus, the row of the details' item marked, and
  // that item named in the address while the details show.
  const restoreList = (ticked) => {
    for (const box of document.querySelectorAll("input[name=item]")) {
      box.checked = ticked.has(box.value);
    }
    focusable();
    const pane = document.getElementById("item-detail");
    const id = pane && pane.dataset.item ? pane.dataset.item : null;
    for (const row of document.querySelectorAll(ROWS)) {
      if (id !== null && row.dataset.item === id) {
        row.setAttribute("aria-current", "true");
      } else {
        row.removeAttribute("aria-current");
      }
    }
    if (detailSwitch && detailSwitch.checked) writeDetail(id);
  };

  // Fetches the page's own address as a page and puts what changed in.
  const refreshPage = async () => {
    const response = await fetch(location.href, {
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "text/html" },
    });
    if (!response.ok || response.redirected) {
      throw new Error(`refresh answered ${response.status}`);
    }
    const fresh = new DOMParser().parseFromString(
      await response.text(), "text/html");
    const ticked = new Set(
      [...document.querySelectorAll("input[name=item]:checked")]
        .map((box) => box.value));
    for (const node of refreshParts(fresh)) htmx.process(node);
    restoreList(ticked);
  };

  // Moves focus to the link that opened the dialog while it is in the
  // page, else to the heading of the details, else to the page's.
  const focusAfterSave = () => {
    if (dialogOpener && dialogOpener.isConnected) {
      dialogOpener.focus();
      return;
    }
    const heading = document.getElementById("item-detail-title")
      || document.querySelector("main h1");
    if (!heading) return;
    heading.tabIndex = -1;
    heading.focus();
  };

  if (dialog && dialogBody) {
    document.addEventListener("click", (event) => {
      if (!plain(event) || !(event.target instanceof Element)) return;
      const link = event.target.closest("a[data-dialog]");
      if (link && typeof htmx !== "undefined") {
        event.preventDefault();
        dialogOpener = link;
        loading = link.href;
        htmx.ajax("GET", link.href,
                  { target: dialogBody, swap: "innerHTML" });
        return;
      }
      const closer = event.target.closest(
        ".lab-dialog-close, #lab-dialog-body .lab-buttons a");
      if (closer && dialog.contains(closer)) {
        event.preventDefault();
        if (!saving) dialog.close();
      }
    });

    // The form is in: show the dialog, or, where the dialog already
    // shows and the form is back with errors, move to the first one.
    dialogBody.addEventListener("htmx:afterSwap", () => {
      loading = null;
      if (!dialog.open) {
        dialog.showModal();
        return;
      }
      const wrong = dialogBody.querySelector(
        ".lab-field--error :is(input, select, textarea)");
      if (wrong) wrong.focus();
    });

    // A form that could not be requested opens as the page it is.
    const unopened = () => {
      if (loading === null) return;
      const href = loading;
      loading = null;
      location.assign(href);
    };
    dialogBody.addEventListener("htmx:responseError", unopened);
    dialogBody.addEventListener("htmx:sendError", unopened);

    dialog.addEventListener("close", () => dialogBody.replaceChildren());
    dialog.addEventListener("cancel", (event) => {
      if (saving) event.preventDefault();
    });

    // htmx enables the buttons again when the save's request ends,
    // which is before the refresh does.
    dialog.addEventListener("htmx:afterRequest", () => {
      if (saving) lockDialog(true);
    });

    document.addEventListener("lab-saved", async (event) => {
      if (!(event.target instanceof Element)
          || !dialog.contains(event.target) || saving) {
        return;
      }
      lockDialog(true);
      try {
        await refreshPage();
      } catch {
        location.reload();
        return;
      }
      lockDialog(false);
      dialog.close();
      focusAfterSave();
    });
  }

  if (!detailSwitch) return;
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
  // keyboard, so the previous item's links cannot be used; once the
  // request ends, swapped or not, the pane in the page is usable. The
  // body's hx-sync aborts a request before the next one starts, so no
  // other row's request is pending then. The pane's class is no guide:
  // until it settles, a swapped-in pane carries the old one's.
  document.addEventListener("htmx:beforeRequest", (event) => {
    const pane = document.getElementById("item-detail");
    if (pane && event.target.matches && event.target.matches(ROWS)) {
      pane.inert = true;
    }
  });
  document.addEventListener("htmx:afterRequest", (event) => {
    const pane = document.getElementById("item-detail");
    if (pane && event.target.matches && event.target.matches(ROWS)) {
      pane.inert = false;
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
