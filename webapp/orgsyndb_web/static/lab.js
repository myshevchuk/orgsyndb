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
// - Marks the item list's layout (.item-layout) data-scripted, so that
//   lab.css follows its data-view and no longer the radio buttons of
//   the switch between the views, `Tabelle` and `Details`
//   (#view-table, #view-details). When one of them changes, the script
//   saves the view in the cookie `item-list-view`, which the server
//   reads, and sets data-view, inside a view transition where the
//   browser has them and the user has not asked for reduced motion.
//   The radio buttons keep their native behaviour. While the details
//   view shows, the button `Spalten` is disabled.
// - In both views, chooses a row: a plain click in it, but not on a
//   link or an input, or an arrow key up or down in the table, which
//   also focuses the row it moves to. Choosing fires the event
//   `item-select` on the row, which makes htmx load the row's details
//   into #item-detail, and nothing else.
// - Once htmx has swapped details in, and once a dialog's save has
//   refreshed the list, makes the list follow the details' item: its
//   row is marked with aria-current="true", and its id is written as
//   `selected` into the address, the filter form's hidden field and
//   the links of the list to itself, which are the column headers, the
//   stock levels and the reset link. A request that is aborted or
//   fails swaps nothing, so pane, mark and address stay as they were.
//   While details load, the pane is inert.
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
//   is reloaded. While the dialog's form is posted, and while that
//   refresh is under way, the dialog's body is inert, so that nothing
//   in it, such as a link to another form, replaces the form whose
//   save is pending.
// - Narrows each batch choice (a select marked data-batch-for, whose
//   options sit in one optgroup per substance, marked data-substance
//   with the substance's key) to the substance of the control that
//   data-batch-for names: the chosen option of an item select, by its
//   data-substance, or the text typed in the new-item form's
//   substance field. It hides and disables the groups of other
//   substances, and clears a chosen batch that it hid. It does so when
//   the page loads and whenever that control changes or is typed in;
//   with no substance, every group shows.
//
// OrgSynLab.place is the placement's arithmetic,
// OrgSynLab.paramSearch the address's and OrgSynLab.narrowBatches the
// batch choice's, each kept apart from the page so that tests can run
// it without one.
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
  // without its leading "?", whose parameter NAME is set to VALUE, a
  // number or text, or removed when VALUE is null; every other
  // parameter keeps its text and its place. It is "?" and the
  // parameters, or "" when none is left. Repeated NAME parameters become
  // one, at the place of the first.
  const paramSearch = (search, name, value) => {
    const kept = [];
    let placed = value === null || value === undefined;
    for (const pair of search.replace(/^\?/, "").split("&")) {
      if (pair === "") continue;
      if (pair.split("=", 1)[0] !== name) {
        kept.push(pair);
      } else if (!placed) {
        kept.push(`${name}=${encodeURIComponent(value)}`);
        placed = true;
      }
    }
    if (!placed) kept.push(`${name}=${encodeURIComponent(value)}`);
    return kept.length ? `?${kept.join("&")}` : "";
  };

  // What narrowing a batch choice to the substance KEY ("" for none)
  // does, given GROUPS, the keys of the choice's optgroups in order,
  // and CHOSEN, the key of the group of the batch chosen, or null for
  // none: the keys of the groups to hide, and whether the chosen batch
  // is to be cleared. With a KEY, every group but its own is hidden
  // and a batch of any other group is cleared; with none, nothing is.
  const narrowBatches = (key, groups, chosen) => ({
    hidden: key === "" ? [] : groups.filter((group) => group !== key),
    clear: key !== "" && chosen !== null && chosen !== key,
  });

  globalThis.OrgSynLab = { place, paramSearch, narrowBatches };
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

  // The key of the substance a control that drives a batch choice
  // holds: the data-substance of an item select's chosen option, or
  // the text of the substance field; "" for none.
  const substanceOf = (control) => {
    if (control.tagName === "SELECT") {
      const option = control.selectedOptions[0];
      return option && option.dataset.substance || "";
    }
    return control.value.trim();
  };

  const narrow = (select) => {
    const driver = select.form
      && select.form.elements.namedItem(select.dataset.batchFor);
    if (!driver) return;
    const groups = [...select.querySelectorAll("optgroup[data-substance]")];
    const option = select.selectedOptions[0];
    const group = option && option.parentElement.matches("optgroup")
      ? option.parentElement.dataset.substance : null;
    const { hidden, clear } = narrowBatches(
      substanceOf(driver), groups.map((each) => each.dataset.substance),
      group);
    for (const each of groups) {
      each.hidden = each.disabled = hidden.includes(each.dataset.substance);
    }
    if (clear) select.value = "";
  };

  for (const select of document.querySelectorAll("select[data-batch-for]")) {
    narrow(select);
  }
  // Delegated, so that each control that drives a choice is heard.
  for (const type of ["change", "input"]) {
    document.addEventListener(type, (event) => {
      const control = event.target;
      if (!(control instanceof Element) || !control.name) return;
      for (const select of document.querySelectorAll(
        "select[data-batch-for]")) {
        if (select.form === control.form
            && select.dataset.batchFor === control.name) {
          narrow(select);
        }
      }
    });
  }

  const layout = document.querySelector(".item-layout");
  const ROWS = ".item-table tbody tr[data-item]";
  // The links of the list to itself, which name the selected item.
  const OWN_LINKS = ".item-table thead a, #stock-entries a, #list-summary a";

  const markedRow = () => document.querySelector(
    `${ROWS}[aria-current="true"]`);

  // The id of the item whose details the pane holds, "" for none.
  const paneItem = () => {
    const pane = document.getElementById("item-detail");
    return pane && pane.dataset.item ? pane.dataset.item : "";
  };

  // Rows take focus, so that the arrow keys have a row to start from.
  const focusable = () => {
    for (const row of document.querySelectorAll(ROWS)) row.tabIndex = -1;
  };

  // Sets the parameter `selected` of the link's address to ID, or
  // removes it when ID is empty, keeping its path.
  const relink = (link, id) => {
    const href = link.getAttribute("href");
    const at = href.indexOf("?");
    link.setAttribute("href", (at < 0 ? href : href.slice(0, at))
      + paramSearch(at < 0 ? "" : href.slice(at), "selected",
                    id === "" ? null : id));
  };

  // Brings the list in step with the details' item ID, "" for none: its
  // row is marked and the others are not, and the address, the filter
  // form's hidden field and the links of the list to itself name it, or
  // do not name any item for no id.
  const follow = (id) => {
    for (const row of document.querySelectorAll(ROWS)) {
      if (id !== "" && row.dataset.item === id) {
        row.setAttribute("aria-current", "true");
      } else {
        row.removeAttribute("aria-current");
      }
    }
    try {
      history.replaceState(
        history.state, "",
        `${location.pathname}${paramSearch(location.search, "selected",
                                           id === "" ? null : id)}`
        + location.hash);
    } catch {
      // The address cannot change: the page shows the item regardless.
    }
    const form = document.getElementById("filters");
    if (form) {
      let field = form.querySelector("input[name=selected]");
      if (id === "") {
        if (field) field.remove();
      } else {
        if (!field) {
          field = document.createElement("input");
          field.type = "hidden";
          field.name = "selected";
          form.append(field);
        }
        field.value = id;
      }
    }
    for (const link of document.querySelectorAll(OWN_LINKS)) {
      relink(link, id);
    }
  };

  // The dialog of the page shell, and what the script knows of the
  // form in it.
  const dialog = document.getElementById("lab-dialog");
  const dialogBody = document.getElementById("lab-dialog-body");
  let dialogOpener = null; // the link that opened the dialog
  let loading = null; // the address of the form being requested
  let saving = false; // a save is posted and its refresh not done
  let posting = false; // the dialog's form is being posted

  // The body takes neither pointer nor keyboard while its form is
  // posted or a save's refresh is under way, so that nothing in it, a
  // link choosing another quarter among them, replaces the form whose
  // save is pending.
  const guardBody = () => {
    dialogBody.inert = posting || saving;
  };

  const lockDialog = (locked) => {
    saving = locked;
    for (const button of dialog.querySelectorAll("button")) {
      button.disabled = locked;
    }
    guardBody();
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
  // ticked, the rows' focus, and the list's follow of the details' item.
  const restoreList = (ticked) => {
    for (const box of document.querySelectorAll("input[name=item]")) {
      box.checked = ticked.has(box.value);
    }
    if (!layout) return;
    focusable();
    follow(paneItem());
  };

  // Fetches the page's own address as a page and puts what changed in.
  const refreshPage = async () => {
    // On the item list the page asks for the item whose details it
    // shows, which the address need not name yet, so that the save
    // keeps it while it is listed.
    const address = layout && paneItem()
      ? `${location.pathname}${paramSearch(location.search, "selected",
                                           paneItem())}`
      : location.href;
    const response = await fetch(address, {
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
      dialogOpener.focus({ preventScroll: true });
      return;
    }
    const heading = document.getElementById("item-detail-title")
      || document.querySelector("main h1");
    if (!heading) return;
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  };

  if (dialog && dialogBody) {
    document.addEventListener("click", (event) => {
      if (!plain(event) || !(event.target instanceof Element)) return;
      const link = event.target.closest("a[data-dialog]");
      if (link && typeof htmx !== "undefined") {
        event.preventDefault();
        // One form at a time: a second click while one loads is lost.
        if (loading !== null || dialog.open) return;
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
        if (!saving && !posting) dialog.close();
      }
    });

    // The form is in: show the dialog, or, where the dialog already
    // shows and the form is back with errors, move to the first one.
    // The form is in: show the dialog when a link of the page asked for
    // it; a form that arrives for a dialog closed meanwhile stays shut.
    dialogBody.addEventListener("htmx:afterSwap", () => {
      const opening = loading !== null;
      loading = null;
      if (!dialog.open && opening) dialog.showModal();
    });

    // A form back with errors: move to the first, once the body takes
    // input again.
    const focusError = () => {
      const wrong = dialogBody.querySelector(
        ".lab-field--error :is(input, select, textarea)");
      if (wrong) wrong.focus();
    };

    // A form that could not be requested opens as the page it is.
    // htmx fires the request's events on its source, the body, not on
    // the dialog it targets.
    const unopened = (event) => {
      if (loading === null || event.detail.target !== dialogBody) return;
      const href = loading;
      loading = null;
      location.assign(href);
    };
    document.addEventListener("htmx:responseError", unopened);
    document.addEventListener("htmx:sendError", unopened);

    dialog.addEventListener("close", () => dialogBody.replaceChildren());
    dialog.addEventListener("cancel", (event) => {
      if (saving || posting) event.preventDefault();
    });

    // While the dialog's form is posted it stays open, so that a save
    // still finds it. A post the server refuses outright, such as one
    // without a session or its CSRF cookie, reloads the page; one that
    // does not reach the server leaves the form as it was, to send
    // again.
    // Only a post counts: a link that loads another form into the
    // dialog leaves it free to close.
    dialog.addEventListener("htmx:beforeRequest", (event) => {
      const config = event.detail.requestConfig;
      if (!config || String(config.verb).toLowerCase() !== "post") return;
      posting = true;
      guardBody();
    });
    dialog.addEventListener("htmx:responseError", () => {
      posting = false;
      location.reload();
    });

    // htmx enables the buttons again when the save's request ends,
    // which is before the refresh does.
    dialog.addEventListener("htmx:afterRequest", () => {
      posting = false;
      if (saving) {
        lockDialog(true);
      } else {
        guardBody();
        if (dialog.open) focusError();
      }
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

  if (!layout) return;

  // From here on lab.css follows data-view, which the radio buttons
  // agree with unless the browser restored them differently.
  layout.dataset.scripted = "";
  const radios = [...document.querySelectorAll("input[name=view]")];
  const checked = radios.find((radio) => radio.checked);
  if (checked) layout.dataset.view = checked.value;
  focusable();

  const columnsButton = document.querySelector(
    "[popovertarget=columns-menu]");
  // The columns of `Spalten` are those of the table view, so the
  // button has nothing to offer while the details view shows.
  const syncColumnsButton = () => {
    if (columnsButton) {
      columnsButton.disabled = layout.dataset.view === "details";
    }
  };
  syncColumnsButton();

  // The view last asked for, which a pending transition may not have
  // shown yet; the transition shows whichever view is asked for last.
  let wanted = layout.dataset.view;
  for (const radio of radios) {
    radio.addEventListener("change", () => {
      if (!radio.checked || wanted === radio.value) return;
      wanted = radio.value;
      document.cookie = `item-list-view=${wanted};`
        + " path=/lab/inventory/end-products/; max-age=31536000;"
        + " SameSite=Lax";
      const show = () => {
        layout.dataset.view = wanted;
        syncColumnsButton();
      };
      if (document.startViewTransition
          && !window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches) {
        document.startViewTransition(show);
      } else {
        show();
      }
    });
  }

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

  // A click chooses the row it lands in unless it lands on a link,
  // which leads where it links, or on an input.
  document.addEventListener("click", (event) => {
    if (typeof htmx === "undefined" || !plain(event)) return;
    if (!(event.target instanceof Element)) return;
    const row = event.target.closest(ROWS);
    if (!row || event.target.closest("a, input")) return;
    choose(row);
  });

  document.addEventListener("keydown", (event) => {
    if (typeof htmx === "undefined") return;
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
    follow(paneItem());
  });
})();
