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
// - On the planning list (.planning-grid), reveals the filter buttons
//   and filters rows in the browser by data-priority, data-action and
//   data-late, updating the shown count, moving the selection to the
//   first shown row when the selected row is hidden, and showing the
//   no-match note when nothing shows while keeping the inspector's
//   article. A plain click in a row (not on other links or buttons) or
//   on its article link, or ArrowUp/ArrowDown in the list over the rows
//   that show, selects the row without loading a page, switches the
//   inspector block matched by data-article, marks the row with
//   aria-current="true", focuses it and writes `selected` into the
//   address with history.replaceState.
//
// OrgSynLab.place is the placement's arithmetic,
// OrgSynLab.paramSearch the address's, OrgSynLab.narrowBatches the
// batch choice's, OrgSynLab.sortOrder the table sorting's, and
// OrgSynLab.planFilterShows and OrgSynLab.planStep the planning list's
// filtering and arrow-key stepping, each kept apart from the page so
// that tests can run it without one.
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

  const NUMBER_KEY = /^[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)$/;
  const ISO_DATE_KEY = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?$/;
  const DE_DATE_KEY = /^(\d{2})\.(\d{2})\.(\d{4})(?:[T ](\d{2}):(\d{2}))?$/;

  const parseSortKey = (rawKey) => {
    const raw = String(rawKey ?? "").trim();
    if (raw === "" || raw === "–") return { group: 3, value: "" };
    if (NUMBER_KEY.test(raw)) {
      return { group: 0, value: Number(raw.replace(",", ".")) };
    }
    let m = ISO_DATE_KEY.exec(raw);
    if (m) {
      const value = m[4] ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}`
        : `${m[1]}-${m[2]}-${m[3]}`;
      return { group: 1, value };
    }
    m = DE_DATE_KEY.exec(raw);
    if (m) {
      const value = m[4] ? `${m[3]}-${m[2]}-${m[1]}T${m[4]}:${m[5]}`
        : `${m[3]}-${m[2]}-${m[1]}`;
      return { group: 1, value };
    }
    return { group: 2, value: raw };
  };

  const makeCollator = (locale) => {
    try {
      if (locale && Intl.Collator.supportedLocalesOf([locale]).length > 0) {
        return new Intl.Collator(locale);
      }
    } catch {
      // Unsupported or invalid locale: fall back to the runtime default.
    }
    return new Intl.Collator();
  };

  // Returns the indices of KEYS in sorted order. Numbers precede dates
  // which precede text (by LOCALE collation) when ascending; DESCENDING
  // reverses that whole order. Empty keys and "–" come last either way,
  // and equal keys keep their original order.
  const sortOrder = (keys, descending = false, locale = undefined) => {
    const collator = makeCollator(locale);
    const items = keys.map((key, index) => ({
      index,
      ...parseSortKey(key),
    }));
    const dir = descending ? -1 : 1;
    items.sort((a, b) => {
      if (a.group === 3 && b.group === 3) return a.index - b.index;
      if (a.group === 3) return 1;
      if (b.group === 3) return -1;
      let cmp = a.group - b.group;
      if (cmp === 0) {
        if (a.group === 0) {
          cmp = a.value - b.value;
        } else if (a.group === 1) {
          cmp = a.value < b.value ? -1 : (a.value > b.value ? 1 : 0);
        } else {
          cmp = collator.compare(a.value, b.value);
        }
      }
      return cmp !== 0 ? cmp * dir : a.index - b.index;
    });
    return items.map((item) => item.index);
  };

  // Whether the planning list's FILTER ("all", "high", "action" or
  // "late") shows ROW ({ priority, action, late }).
  const planFilterShows = (row, filter) => {
    if (filter === "high") return row.priority === "high";
    if (filter === "action") return Boolean(row.action);
    if (filter === "late") return Boolean(row.late);
    return true;
  };

  // The index of the nearest shown row before ("ArrowUp") or after
  // ("ArrowDown") CURRENT in SHOWN, a list of booleans in current row
  // order; returns CURRENT when none lies in that direction.
  const planStep = (shown, current, key) => {
    if (key === "ArrowDown") {
      for (let i = current + 1; i < shown.length; i += 1) {
        if (shown[i]) return i;
      }
      return current;
    }
    if (key === "ArrowUp") {
      for (let i = Math.min(current - 1, shown.length - 1); i >= 0; i -= 1) {
        if (shown[i]) return i;
      }
      return current;
    }
    return current;
  };

  globalThis.OrgSynLab = {
    place, paramSearch, narrowBatches, sortOrder, planFilterShows, planStep,
  };
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

  // Wraps each visible header of every table[data-sortable] in ROOT in
  // a button.sort-header so keyboard and pointer activate it.
  const enhanceSortable = (root) => {
    const tables = [];
    if (root instanceof Element && root.matches("table[data-sortable]")) {
      tables.push(root);
    }
    tables.push(...root.querySelectorAll("table[data-sortable]"));
    for (const table of tables) {
      const headRow = table.tHead && table.tHead.rows[0];
      if (!headRow) continue;
      for (const th of headRow.cells) {
        if (th.querySelector(":scope > button.sort-header")) continue;
        const hidden = th.querySelector(".visually-hidden");
        const visible = hidden
          ? th.textContent.replace(hidden.textContent, "").trim()
          : th.textContent.trim();
        if (!visible) continue;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "sort-header";
        button.append(...th.childNodes);
        th.append(button);
      }
    }
  };

  const sortTable = (table, colIndex, descending) => {
    const tbody = table.tBodies[0];
    const headRow = table.tHead && table.tHead.rows[0];
    if (!tbody || !headRow) return;
    const headers = [...headRow.cells];
    const th = headers[colIndex];
    if (!th) return;
    const rows = [...tbody.rows];
    const keys = rows.map((row) => {
      const cell = row.cells[colIndex];
      if (!cell) return "";
      return cell.hasAttribute("data-sort")
        ? cell.getAttribute("data-sort")
        : cell.textContent;
    });
    const order = sortOrder(keys, descending,
                            document.documentElement.lang || undefined);
    for (const idx of order) tbody.append(rows[idx]);
    for (const header of headers) header.removeAttribute("aria-sort");
    th.setAttribute("aria-sort", descending ? "descending" : "ascending");
  };

  enhanceSortable(document);
  document.addEventListener("click", (event) => {
    if (!plain(event) || !(event.target instanceof Element)) return;
    const button = event.target.closest(
      "table[data-sortable] thead th > button.sort-header");
    if (!button) return;
    const th = button.parentElement;
    const table = th.closest("table[data-sortable]");
    const colIndex = [...th.parentElement.cells].indexOf(th);
    const descending = th.getAttribute("aria-sort") === "ascending";
    sortTable(table, colIndex, descending);
  });

  // Fallback for browsers without ::details-content print support: open
  // closed collapsible widgets on beforeprint and close them afterwards.
  let openedForPrint = [];
  window.addEventListener("beforeprint", () => {
    openedForPrint = [];
    for (const el of document.querySelectorAll("details.widget:not([open])")) {
      el.open = true;
      openedForPrint.push(el);
    }
  });
  window.addEventListener("afterprint", () => {
    for (const el of openedForPrint) {
      if (el.isConnected) el.open = false;
    }
    openedForPrint = [];
  });

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
    const widgetOpen = new Map(
      [...document.querySelectorAll("details.widget[id]")]
        .map((el) => [el.id, el.open]));
    const tableSort = new Map();
    for (const table of document.querySelectorAll(
      "table[data-sortable][id]")) {
      const sorted = table.tHead
        && table.tHead.querySelector("th[aria-sort]");
      if (sorted) {
        tableSort.set(table.id, {
          colIndex: [...sorted.parentElement.cells].indexOf(sorted),
          descending: sorted.getAttribute("aria-sort") === "descending",
        });
      }
    }
    const boxScroll = new Map();
    for (const box of document.querySelectorAll(".table-scroll")) {
      const table = box.id ? null : box.querySelector("table[id]");
      const id = box.id || (table && table.id);
      if (id && (box.scrollTop || box.scrollLeft)) {
        boxScroll.set(id, {
          byBox: Boolean(box.id),
          top: box.scrollTop,
          left: box.scrollLeft,
        });
      }
    }
    for (const node of refreshParts(fresh)) {
      htmx.process(node);
      enhanceSortable(node);
    }
    for (const [id, isOpen] of widgetOpen) {
      const el = document.getElementById(id);
      if (el && el.matches("details.widget")) el.open = isOpen;
    }
    for (const [id, state] of tableSort) {
      const table = document.getElementById(id);
      if (table && table.matches("table[data-sortable]")) {
        sortTable(table, state.colIndex, state.descending);
      }
    }
    for (const [id, pos] of boxScroll) {
      const el = document.getElementById(id);
      const box = pos.byBox ? el : el && el.closest(".table-scroll");
      if (box) {
        box.scrollTop = pos.top;
        box.scrollLeft = pos.left;
      }
    }
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

  const planGrid = document.querySelector(".planning-grid");
  const planTable = planGrid && planGrid.querySelector("table[data-sortable]");
  const planBody = planTable && planTable.tBodies[0];
  if (planGrid && planTable && planBody) {
    const planCount = planGrid.querySelector("[data-planning-count]");
    const planFilterGroup = planGrid.querySelector(".planning-filters");
    const planNoMatch = planGrid.querySelector(".planning-no-match");

    const planRows = () => [...planBody.querySelectorAll("tr[data-article]")];
    const planBlocks = () => [
      ...planGrid.querySelectorAll("[data-article]"),
    ].filter((el) => el.tagName !== "TR");

    for (const row of planRows()) row.tabIndex = -1;
    if (planFilterGroup) planFilterGroup.hidden = false;

    const selectPlanRow = (row, focusMode = null) => {
      const article = row.dataset.article;
      for (const each of planRows()) {
        if (each === row) {
          each.setAttribute("aria-current", "true");
        } else {
          each.removeAttribute("aria-current");
        }
      }
      for (const block of planBlocks()) {
        block.hidden = block.dataset.article !== article;
      }
      try {
        history.replaceState(
          history.state, "",
          `${location.pathname}${paramSearch(location.search, "selected",
                                             article)}`
          + location.hash);
      } catch {
        // The address cannot change: the page shows the article regardless.
      }
      if (focusMode === "click") {
        row.focus({ preventScroll: true });
      } else if (focusMode === "key") {
        row.focus();
      }
    };

    planTable.addEventListener("click", (event) => {
      if (!plain(event) || !(event.target instanceof Element)) return;
      const row = event.target.closest("tbody tr[data-article]");
      if (!row || !planBody.contains(row)) return;
      const selectLink = event.target.closest("a.planning-select");
      if (selectLink && row.contains(selectLink)) {
        event.preventDefault();
      } else if (event.target.closest("a, button, input, select, textarea")) {
        return;
      }
      selectPlanRow(row, "click");
    });

    planTable.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
        return;
      }
      const rows = planRows();
      const shown = rows.map((row) => !row.hidden);
      const focused = event.target instanceof Element
        ? event.target.closest("tbody tr[data-article]") : null;
      const marked = rows.find(
        (row) => row.getAttribute("aria-current") === "true") || null;
      const current = rows.indexOf(focused && planBody.contains(focused)
        ? focused : marked);
      const next = planStep(shown, current, event.key);
      event.preventDefault();
      if (next >= 0 && rows[next] && shown[next]
          && (next !== current || rows[next] !== marked)) {
        selectPlanRow(rows[next], "key");
      }
    });

    if (planFilterGroup) {
      planFilterGroup.addEventListener("click", (event) => {
        if (!plain(event) || !(event.target instanceof Element)) return;
        const button = event.target.closest("button[data-plan-filter]");
        if (!button || !planFilterGroup.contains(button)) return;
        const filter = button.dataset.planFilter;
        for (const each of planFilterGroup.querySelectorAll(
          "button[data-plan-filter]")) {
          each.setAttribute(
            "aria-pressed",
            each.dataset.planFilter === filter ? "true" : "false");
        }
        let shownCount = 0;
        let firstShown = null;
        let selectedHidden = false;
        for (const row of planRows()) {
          const visible = planFilterShows({
            priority: row.dataset.priority || "",
            action: row.dataset.action === "1",
            late: row.dataset.late === "1",
          }, filter);
          row.hidden = !visible;
          if (visible) {
            shownCount += 1;
            if (!firstShown) firstShown = row;
          } else if (row.getAttribute("aria-current") === "true") {
            selectedHidden = true;
          }
        }
        if (planCount) planCount.textContent = String(shownCount);
        if (planNoMatch) planNoMatch.hidden = shownCount > 0;
        if (selectedHidden && firstShown) {
          selectPlanRow(firstShown);
        }
      });
    }
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
