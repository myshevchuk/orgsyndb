// The lab application's script, loaded with defer on every page of the
// shell after htmx, idiomorph, and Stimulus.
//
// Exports five pure helpers on globalThis.OrgSynLab (place, paramSearch,
// narrowBatches, sortOrder, planStep) so tests can run them without a
// DOM. In a browser document, installs the no-eval htmx morph extension,
// print-time collapsible widget fallback, and live-list document guards,
// then starts Stimulus with actionAttribute "data-lab-action" and
// registers six controllers:
//   - popover-anchor: CSS Anchor Positioning with OrgSynLab.place fallback
//   - batch-narrow: substance-scoped optgroup narrowing on [data-batch-for]
//   - sortable-table: client-side sorting on table[data-sortable]
//   - master-detail: nestable row selection, stepping, and view switching
//   - split: golden-ratio major-side toggle persisted per list
//   - dialog: shell modal lifecycle and in-place [data-refresh] morphing
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

  // The decoded name of the query pair PAIR, or its raw name when it
  // does not decode.
  const paramName = (pair) => {
    const raw = pair.split("=", 1)[0];
    try {
      return decodeURIComponent(raw.replace(/\+/g, " "));
    } catch {
      return raw;
    }
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
      if (paramName(pair) !== name) {
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
  // is to be cleared.
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
    place, paramSearch, narrowBatches, sortOrder, planStep,
  };
  if (typeof document === "undefined") return;

  const plain = (event) => event.button === 0 && !event.ctrlKey
    && !event.metaKey && !event.shiftKey && !event.altKey;

  const supportsAnchor = () =>
    typeof CSS !== "undefined"
    && typeof CSS.supports === "function"
    && CSS.supports("anchor-name", "--a")
    && CSS.supports("position-anchor", "--a")
    && CSS.supports("top", "anchor(bottom)")
    && CSS.supports("position-try-fallbacks", "flip-block");

  // Restrict htmx's morph extension to the three literal styles so no
  // custom morph: suffix ever reaches Function() under allowEval: false.
  const setupMorphExtension = () => {
    if (typeof htmx === "undefined" || typeof Idiomorph === "undefined") {
      return;
    }
    const morphConfig = (swapStyle) => {
      if (swapStyle === "morph" || swapStyle === "morph:outerHTML") {
        return { morphStyle: "outerHTML" };
      }
      if (swapStyle === "morph:innerHTML") {
        return { morphStyle: "innerHTML" };
      }
      return null;
    };
    htmx.defineExtension("morph", {
      isInlineSwap: (swapStyle) => {
        const config = morphConfig(swapStyle);
        return Boolean(config && config.morphStyle === "outerHTML");
      },
      handleSwap: (swapStyle, target, fragment) => {
        const config = morphConfig(swapStyle);
        if (config) {
          return Idiomorph.morph(target, fragment.children, config);
        }
        return false;
      },
    });
  };

  // Fallback for browsers without ::details-content print support: open
  // closed collapsible widgets on beforeprint and close them afterwards.
  const setupPrintWidgets = () => {
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
  };

  // Document-level guards for live-filtered lists: hide fallback submit
  // buttons, cancel stale debounced searches after newer #main:replace
  // requests, preserve freshly typed search text across older OOB swaps,
  // restore applied filter controls when row selection cancels a filter,
  // and keep modified/non-primary clicks native on a[href][hx-get].
  const setupLiveListGuards = () => {
    const hideLiveSubmits = (root = document) => {
      for (const form of root.querySelectorAll("form.lab-filters[hx-get]")) {
        for (const button of form.querySelectorAll("button[type=submit]")) {
          button.hidden = true;
        }
      }
    };
    hideLiveSubmits();
    document.addEventListener("htmx:afterSettle", () => hideLiveSubmits());

    let actionSeq = 0;
    let lastInputSeq = 0;
    let filterInFlight = false;
    let pendingSearch = null;
    let appliedFilters = null;

    const liveFilterForm = () =>
      document.querySelector("form.lab-filters[hx-get]");

    const snapshotFilters = () => {
      const form = liveFilterForm();
      if (!form || !form.elements) return;
      const prev = appliedFilters;
      const next = new Map();
      const keepAppliedSearch = lastInputSeq > 0 && lastInputSeq === actionSeq;
      for (const control of form.elements) {
        if (!control || !control.name) continue;
        if (control.type === "hidden" || control.type === "submit") continue;
        if (control.type === "checkbox") {
          next.set(control.name, { kind: "checkbox", value: control.checked });
        } else if (control.id === "filter-q" && keepAppliedSearch
                   && prev && prev.has(control.name)) {
          next.set(control.name, prev.get(control.name));
        } else {
          next.set(control.name, { kind: "value", value: control.value });
        }
      }
      appliedFilters = next;
    };

    const restoreFilters = () => {
      const form = liveFilterForm();
      if (!form || !form.elements || !appliedFilters) return;
      for (const control of form.elements) {
        if (!control || !control.name || !appliedFilters.has(control.name)) {
          continue;
        }
        const saved = appliedFilters.get(control.name);
        if (saved.kind === "checkbox") {
          control.checked = saved.value;
        } else {
          control.value = saved.value;
        }
      }
    };

    snapshotFilters();

    document.addEventListener("input", (event) => {
      if (event.target instanceof Element
          && event.target.matches("#filter-q")) {
        lastInputSeq = ++actionSeq;
      }
    });
    document.addEventListener("htmx:beforeRequest", (event) => {
      const elt = event.detail && event.detail.elt;
      if (elt instanceof Element && elt.matches("form.lab-filters[hx-get]")) {
        filterInFlight = true;
      }
    });
    for (const type of [
      "htmx:afterRequest", "htmx:responseError", "htmx:sendError",
      "htmx:abort",
    ]) {
      document.addEventListener(type, (event) => {
        const elt = event.detail && event.detail.elt;
        if (elt instanceof Element
            && elt.matches("form.lab-filters[hx-get]")) {
          filterInFlight = false;
        }
      });
    }
    document.addEventListener("htmx:oobBeforeSwap", (event) => {
      const target = event.detail && event.detail.target;
      if (!target || target.id !== "filters") return;
      if (lastInputSeq > 0 && lastInputSeq === actionSeq) {
        const input = document.getElementById("filter-q");
        if (input) {
          pendingSearch = {
            value: input.value,
            start: input.selectionStart,
            end: input.selectionEnd,
          };
        }
      }
    });
    document.addEventListener("htmx:oobAfterSwap", (event) => {
      const target = event.detail && event.detail.target;
      if (!target || target.id !== "filters" || !pendingSearch) return;
      const input = document.getElementById("filter-q");
      if (input) {
        input.value = pendingSearch.value;
        if (typeof input.setSelectionRange === "function"
            && typeof pendingSearch.start === "number"
            && typeof pendingSearch.end === "number"
            && document.activeElement === input) {
          input.setSelectionRange(pendingSearch.start, pendingSearch.end);
        }
      }
      pendingSearch = null;
    });
    document.addEventListener("htmx:afterSettle", (event) => {
      const target = event.detail && event.detail.target;
      if (target && target.id === "item-rows") {
        snapshotFilters();
      }
    });
    document.addEventListener("htmx:confirm", (event) => {
      const detail = event.detail;
      const elt = detail && detail.elt;
      if (!(elt instanceof Element)) return;
      const trigType = detail.triggeringEvent && detail.triggeringEvent.type;
      if (elt.matches("form.lab-filters[hx-get]") && trigType === "input"
          && lastInputSeq < actionSeq) {
        event.preventDefault();
        return;
      }
      if (elt.matches("tr[data-item][hx-get]")
          && (filterInFlight
              || (lastInputSeq > 0 && lastInputSeq === actionSeq))) {
        restoreFilters();
        filterInFlight = false;
      }
      const syncHost = elt.getAttribute("hx-sync") === "#main:replace"
        ? elt
        : (elt.closest ? elt.closest("[hx-sync]") : null);
      if (syncHost && syncHost.getAttribute("hx-sync") === "#main:replace") {
        actionSeq += 1;
      }
    });

    document.addEventListener("click", (event) => {
      if (plain(event) || !(event.target instanceof Element)) return;
      if (event.target.closest("a[href][hx-get]")) {
        event.stopPropagation();
      }
    }, true);
  };

  setupMorphExtension();
  setupPrintWidgets();
  setupLiveListGuards();

  if (typeof Stimulus === "undefined") return;

  // Shared helpers used across controllers.
  const substanceOf = (control) => {
    if (control.tagName === "SELECT") {
      const option = control.selectedOptions[0];
      return (option && option.dataset.substance) || "";
    }
    return control.value.trim();
  };

  const narrow = (select) => {
    const driver = select.form
      && select.form.elements.namedItem(select.dataset.batchFor);
    if (!driver) return;
    const groups = [...select.querySelectorAll("optgroup[data-substance]")];
    const option = select.selectedOptions[0];
    const group = option && option.parentElement
      && option.parentElement.matches("optgroup")
      ? option.parentElement.dataset.substance : null;
    const { hidden, clear } = narrowBatches(
      substanceOf(driver), groups.map((each) => each.dataset.substance),
      group);
    for (const each of groups) {
      each.hidden = each.disabled = hidden.includes(each.dataset.substance);
    }
    if (clear) select.value = "";
  };

  const makeFocusable = (rows) => {
    for (const row of rows) row.tabIndex = -1;
  };

  const markCurrent = (rows, active) => {
    for (const row of rows) {
      if (row === active) {
        row.setAttribute("aria-current", "true");
      } else {
        row.removeAttribute("aria-current");
      }
    }
  };

  const replaceParam = (name, value) => {
    try {
      history.replaceState(
        history.state, "",
        `${location.pathname}${paramSearch(location.search, name,
                                           value === "" ? null : value)}`
        + location.hash);
    } catch {
      // The address cannot change: the page shows the selection regardless.
    }
  };

  const setHiddenParam = (name, value) => {
    const host = document.getElementById("filter-selected")
      || document.getElementById("filters");
    if (!host) return;
    let field = host.querySelector(`input[name=${name}]`);
    if (value === "" || value === null || value === undefined) {
      if (field) field.remove();
    } else {
      if (!field) {
        field = document.createElement("input");
        field.type = "hidden";
        field.name = name;
        host.append(field);
      }
      field.value = value;
    }
  };

  const stepIndex = (rows, shown, from, key) =>
    planStep(shown, rows.indexOf(from), key);

  const OWN_LINKS = ".main-table thead a, #stock-entries a, #list-summary a";

  const paneItemOf = (paneId) => {
    const pane = document.getElementById(paneId);
    return pane && pane.dataset.item ? pane.dataset.item : "";
  };

  const relinkParam = (link, name, value) => {
    const href = link.getAttribute("href");
    if (!href) return;
    const at = href.indexOf("?");
    const next = (at < 0 ? href : href.slice(0, at))
      + paramSearch(at < 0 ? "" : href.slice(at), name,
                    value === "" ? null : value);
    link.setAttribute("href", next);
    if (link.hasAttribute("hx-get")) {
      link.setAttribute("hx-get", next);
    }
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

  const REFRESH_MORPH = {
    callbacks: {
      beforeAttributeUpdated: (attr, node) => !(
        attr === "open" && node.matches("details.widget")
      ),
    },
  };

  // Morphs every element of the page marked data-refresh in place
  // against the matching element of FRESH, replaces the messages, and
  // returns the morphed elements. An element FRESH lacks is removed.
  const refreshParts = (fresh) => {
    const added = [];
    for (const old of document.querySelectorAll("[data-refresh][id]")) {
      const next = fresh.getElementById(old.id);
      if (next) {
        Idiomorph.morph(old, next, REFRESH_MORPH);
        added.push(old);
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

  // Positions .lab-popup[popover] elements via OrgSynLab.place when the
  // browser lacks full CSS Anchor Positioning.
  class PopoverAnchorController extends Stimulus.Controller {
    connect() {
      this._open = false;
      this._onReposition = () => this._reposition();
      this._onToggle = (event) => {
        if (event.newState === "open") {
          if (!supportsAnchor()) {
            this._open = true;
            this.element.dataset.placed = "";
            this._reposition();
            document.addEventListener("scroll", this._onReposition, true);
            window.addEventListener("resize", this._onReposition);
          }
        } else {
          this._detachPositionListeners();
        }
      };
      this.element.addEventListener("toggle", this._onToggle);
    }

    disconnect() {
      this.element.removeEventListener("toggle", this._onToggle);
      this._detachPositionListeners();
    }

    _detachPositionListeners() {
      if (!this._open) return;
      this._open = false;
      document.removeEventListener("scroll", this._onReposition, true);
      window.removeEventListener("resize", this._onReposition);
    }

    _reposition() {
      if (!this._open) return;
      const button = [...document.querySelectorAll("[popovertarget]")]
        .find((el) => el.getAttribute("popovertarget") === this.element.id
              && !this.element.contains(el));
      if (!button) return;
      const spot = place(
        button.getBoundingClientRect(),
        { width: this.element.offsetWidth, height: this.element.offsetHeight },
        { width: document.documentElement.clientWidth,
          height: window.innerHeight });
      this.element.style.left = `${spot.left}px`;
      this.element.style.top = `${spot.top}px`;
    }
  }

  // Narrows a select[data-batch-for] to the substance of its named
  // driver control in the same form.
  class BatchNarrowController extends Stimulus.Controller {
    connect() {
      this._form = this.element.form;
      this._onDriverEvent = (event) => {
        const control = event.target;
        if (control instanceof Element
            && control.name === this.element.dataset.batchFor) {
          narrow(this.element);
        }
      };
      narrow(this.element);
      if (this._form) {
        this._form.addEventListener("change", this._onDriverEvent);
        this._form.addEventListener("input", this._onDriverEvent);
      }
    }

    disconnect() {
      if (this._form && this._onDriverEvent) {
        this._form.removeEventListener("change", this._onDriverEvent);
        this._form.removeEventListener("input", this._onDriverEvent);
      }
      this._form = null;
      this._onDriverEvent = null;
    }
  }

  // Enhances a table[data-sortable] with sort buttons and sorts on click.
  class SortableTableController extends Stimulus.Controller {
    connect() {
      enhanceSortable(this.element);
      this._onClick = (event) => {
        if (!plain(event) || !(event.target instanceof Element)) return;
        const button = event.target.closest("thead th > button.sort-header");
        if (!button || !this.element.contains(button)) return;
        const th = button.parentElement;
        if (th.closest("table[data-sortable]") !== this.element) return;
        const colIndex = [...th.parentElement.cells].indexOf(th);
        const descending = th.getAttribute("aria-sort") === "ascending";
        sortTable(this.element, colIndex, descending);
      };
      this.element.addEventListener("click", this._onClick);
      // A morph keeps the table but drops its script-added buttons.
      this._onSettle = () => enhanceSortable(this.element);
      document.addEventListener("htmx:afterSettle", this._onSettle);
    }

    disconnect() {
      this.element.removeEventListener("click", this._onClick);
      document.removeEventListener("htmx:afterSettle", this._onSettle);
    }
  }

  // Nestable master-detail controller binding one tbody's rows to one
  // details pane and one URL parameter. The outer level also owns the
  // page's view switch, stock-menu dismissal, and ticked item boxes.
  class MasterDetailController extends Stimulus.Controller {
    static values = {
      level: String,
      rows: String,
      pane: String,
      param: String,
    };

    _isOuter() {
      return this.levelValue !== "inner";
    }

    _rowSelector() {
      return `#${this.rowsValue} > tr[data-item]`;
    }

    _rows() {
      return [...this.element.querySelectorAll(this._rowSelector())];
    }

    _paneItem() {
      return paneItemOf(this.paneValue);
    }

    _syncRows(id) {
      const rows = this._rows();
      makeFocusable(rows);
      const active = id !== ""
        ? rows.find((row) => row.dataset.item === id) || null
        : null;
      markCurrent(rows, active);
    }

    _syncParam(name, value) {
      replaceParam(name, value);
      setHiddenParam(name, value);
      for (const link of document.querySelectorAll(OWN_LINKS)) {
        relinkParam(link, name, value);
      }
    }

    _follow(id) {
      this._syncRows(id);
      this._syncParam(this.paramValue, id);
      if (this._isOuter()) {
        const lot = paneItemOf("lot-detail");
        if (lot || document.querySelector("#filter-selected input[name=lot]")
            || new URLSearchParams(location.search).has("lot")) {
          this._syncParam("lot", lot);
        }
      }
    }

    restoreAfterRefresh(ticked) {
      if (this._isOuter()) {
        for (const box of document.querySelectorAll("input[name=item]")) {
          box.checked = ticked.has(box.value);
        }
      }
      this._follow(this._paneItem());
    }

    connect() {
      makeFocusable(this._rows());
      this._radios = null;
      this._liveTicked = null;

      if (this._isOuter()) {
        this.element.dataset.scripted = "";
        this._radios = [...document.querySelectorAll("input[name=view]")];
        const checked = this._radios.find((radio) => radio.checked);
        if (checked) this.element.dataset.view = checked.value;
        this._wanted = this.element.dataset.view;

        this._onRadioChange = (event) => {
          const radio = event.currentTarget;
          if (!radio.checked) return;
          const major = radio.dataset.major || "";
          if (major) {
            // Written even when unchanged here: another tab may have
            // stored the other side.
            this.element.dataset.major = major;
            const split = this.element.dataset.splitCookie;
            if (split) {
              document.cookie = `${split}=${major};`
                + ` path=${location.pathname}; max-age=31536000;`
                + " SameSite=Lax";
            }
          }
          if (this._wanted === radio.value) return;
          this._wanted = radio.value;
          const cookie = this.element.dataset.cookie || "item-list-view";
          document.cookie = `${cookie}=${this._wanted};`
            + ` path=${location.pathname}; max-age=31536000;`
            + " SameSite=Lax";
          const show = () => {
            this.element.dataset.view = this._wanted;
          };
          if (document.startViewTransition
              && !window.matchMedia("(prefers-reduced-motion: reduce)")
                .matches) {
            document.startViewTransition(show);
          } else {
            show();
          }
        };
        for (const radio of this._radios) {
          radio.addEventListener("change", this._onRadioChange);
        }

        this._onConfigRequest = (event) => {
          const elt = event.detail && event.detail.elt;
          if (elt instanceof Element && elt.matches(OWN_LINKS)) {
            const next = elt.getAttribute("hx-get");
            if (next) event.detail.path = next;
          }
        };
        this._onBeforeSwap = (event) => {
          if (event.detail && event.detail.target
              && event.detail.target.id === this.rowsValue) {
            this._liveTicked = new Set(
              [...document.querySelectorAll("input[name=item]:checked")]
                .map((box) => box.value));
          }
        };
        document.addEventListener("htmx:configRequest", this._onConfigRequest);
        document.addEventListener("htmx:beforeSwap", this._onBeforeSwap);
      }

      this._onBeforeRequest = (event) => {
        const pane = document.getElementById(this.paneValue);
        if (pane && event.target && event.target.matches
            && event.target.matches(this._rowSelector())) {
          pane.inert = true;
        }
      };
      this._onAfterRequest = (event) => {
        const pane = document.getElementById(this.paneValue);
        if (pane && event.target && event.target.matches
            && event.target.matches(this._rowSelector())) {
          pane.inert = false;
        }
      };
      this._onClick = (event) => {
        if (!(event.target instanceof Element)) return;
        if (this._isOuter()
            && event.target.closest("#stock-menu a[hx-get]")) {
          const menu = document.getElementById("stock-menu");
          if (menu && typeof menu.hidePopover === "function") {
            try {
              menu.hidePopover();
            } catch {
              // Already closed.
            }
          }
          return;
        }
        if (typeof htmx === "undefined" || !plain(event)) return;
        const row = event.target.closest(this._rowSelector());
        if (!row || !this.element.contains(row) || event.target.closest(
          "a, button, label, input, select, textarea")) {
          return;
        }
        row.focus({ preventScroll: true });
        htmx.trigger(row, "item-select");
      };
      this._onKeydown = (event) => {
        if (typeof htmx === "undefined") return;
        if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
          return;
        }
        if (!(event.target instanceof Element)) return;
        const body = document.getElementById(this.rowsValue);
        const table = body && body.closest("table");
        if (!table || event.target.closest("table") !== table) return;
        const rows = this._rows();
        const marked = rows.find(
          (row) => row.getAttribute("aria-current") === "true") || null;
        const from = event.target.closest(this._rowSelector()) || marked;
        if (!from) return;
        event.preventDefault();
        const shown = rows.map((row) => !row.hidden);
        const current = rows.indexOf(from);
        const next = stepIndex(rows, shown, from, event.key);
        if (next < 0 || next === current || !rows[next]) return;
        rows[next].focus();
        htmx.trigger(rows[next], "item-select");
      };
      this._onAfterSwap = (event) => {
        const target = event.detail && event.detail.target;
        if (target && target.id === this.rowsValue) {
          if (this._isOuter() && this._liveTicked) {
            for (const box of document.querySelectorAll("input[name=item]")) {
              box.checked = this._liveTicked.has(box.value);
            }
            this._liveTicked = null;
          }
          makeFocusable(this._rows());
          return;
        }
        const row = event.detail && event.detail.requestConfig
          && event.detail.requestConfig.elt;
        if (row && row.matches && row.matches(this._rowSelector())) {
          this._follow(this._paneItem());
          return;
        }
        makeFocusable(this._rows());
      };
      this._onRefocusable = () => this._syncRows(this._paneItem());

      document.addEventListener("htmx:beforeRequest", this._onBeforeRequest);
      document.addEventListener("htmx:afterRequest", this._onAfterRequest);
      document.addEventListener("click", this._onClick);
      document.addEventListener("keydown", this._onKeydown);
      document.addEventListener("htmx:afterSwap", this._onAfterSwap);
      document.addEventListener("htmx:oobAfterSwap", this._onRefocusable);
      document.addEventListener("htmx:afterSettle", this._onRefocusable);
    }

    disconnect() {
      if (this._radios) {
        for (const radio of this._radios) {
          radio.removeEventListener("change", this._onRadioChange);
        }
      }
      if (this._onConfigRequest) {
        document.removeEventListener(
          "htmx:configRequest", this._onConfigRequest);
      }
      if (this._onBeforeSwap) {
        document.removeEventListener("htmx:beforeSwap", this._onBeforeSwap);
      }
      document.removeEventListener(
        "htmx:beforeRequest", this._onBeforeRequest);
      document.removeEventListener("htmx:afterRequest", this._onAfterRequest);
      document.removeEventListener("click", this._onClick);
      document.removeEventListener("keydown", this._onKeydown);
      document.removeEventListener("htmx:afterSwap", this._onAfterSwap);
      document.removeEventListener("htmx:oobAfterSwap", this._onRefocusable);
      document.removeEventListener("htmx:afterSettle", this._onRefocusable);
    }
  }

  // Manages the page shell's #lab-dialog modal and in-place page refresh
  // on lab-saved.
  class DialogController extends Stimulus.Controller {
    connect() {
      this._body = document.getElementById("lab-dialog-body");
      if (!this._body) return;
      this._opener = null;
      this._openerHref = "";
      this._openerInPopover = false;
      this._openerPane = "";
      this._loading = null;
      this._saving = false;
      this._posting = false;

      this._onDocClick = (event) => {
        if (!plain(event) || !(event.target instanceof Element)) return;
        const link = event.target.closest("a[data-dialog]");
        if (link && typeof htmx !== "undefined") {
          event.preventDefault();
          if (this._loading !== null || this.element.open) return;
          this._opener = link;
          this._openerHref = link.getAttribute("href") || "";
          this._openerInPopover = Boolean(link.closest("[popover]"));
          const pane = link.closest("#lot-detail, #item-detail");
          this._openerPane = pane ? pane.id : "";
          let openPopover = link.closest("[popover]");
          try {
            if (openPopover && !openPopover.matches(":popover-open")) {
              openPopover = null;
            }
          } catch {
            // A browser without :popover-open has no open popover.
            openPopover = null;
          }
          if (openPopover && typeof openPopover.hidePopover === "function") {
            try {
              openPopover.hidePopover();
            } catch {
              // Already closed.
            }
          }
          this._loading = link.href;
          htmx.ajax("GET", link.href,
                    { target: this._body, swap: "innerHTML" });
          return;
        }
        const closer = event.target.closest(
          ".lab-dialog-close, #lab-dialog-body .lab-buttons a");
        if (closer && this.element.contains(closer)) {
          event.preventDefault();
          if (!this._saving && !this._posting) this.element.close();
        }
      };

      this._onBodyAfterSwap = () => {
        const opening = this._loading !== null;
        this._loading = null;
        if (!this.element.open && opening) this.element.showModal();
      };

      this._onUnopened = (event) => {
        if (this._loading === null
            || !event.detail || event.detail.target !== this._body) {
          return;
        }
        const href = this._loading;
        this._loading = null;
        location.assign(href);
      };

      this._onClose = () => this._body.replaceChildren();
      this._onCancel = (event) => {
        if (this._saving || this._posting) event.preventDefault();
      };

      this._onBeforeRequest = (event) => {
        const config = event.detail && event.detail.requestConfig;
        if (!config || String(config.verb).toLowerCase() !== "post") return;
        this._posting = true;
        this._guardBody();
      };

      this._onDialogResponseError = () => {
        this._posting = false;
        location.reload();
      };

      this._onAfterRequest = () => {
        this._posting = false;
        if (this._saving) {
          this._lockDialog(true);
        } else {
          this._guardBody();
          if (this.element.open) this._focusError();
        }
      };

      this._onSaved = async (event) => {
        if (!(event.target instanceof Element)
            || !this.element.contains(event.target) || this._saving) {
          return;
        }
        this._lockDialog(true);
        try {
          await this._refreshPage();
        } catch {
          location.reload();
          return;
        }
        this._lockDialog(false);
        this.element.close();
        this._focusAfterSave();
      };

      document.addEventListener("click", this._onDocClick);
      document.addEventListener("htmx:responseError", this._onUnopened);
      document.addEventListener("htmx:sendError", this._onUnopened);
      document.addEventListener("lab-saved", this._onSaved);
      this._body.addEventListener("htmx:afterSwap", this._onBodyAfterSwap);
      this.element.addEventListener("close", this._onClose);
      this.element.addEventListener("cancel", this._onCancel);
      this.element.addEventListener(
        "htmx:beforeRequest", this._onBeforeRequest);
      this.element.addEventListener(
        "htmx:responseError", this._onDialogResponseError);
      this.element.addEventListener("htmx:afterRequest", this._onAfterRequest);
    }

    disconnect() {
      if (!this._body) return;
      document.removeEventListener("click", this._onDocClick);
      document.removeEventListener("htmx:responseError", this._onUnopened);
      document.removeEventListener("htmx:sendError", this._onUnopened);
      document.removeEventListener("lab-saved", this._onSaved);
      this._body.removeEventListener("htmx:afterSwap", this._onBodyAfterSwap);
      this.element.removeEventListener("close", this._onClose);
      this.element.removeEventListener("cancel", this._onCancel);
      this.element.removeEventListener(
        "htmx:beforeRequest", this._onBeforeRequest);
      this.element.removeEventListener(
        "htmx:responseError", this._onDialogResponseError);
      this.element.removeEventListener(
        "htmx:afterRequest", this._onAfterRequest);
      this._body = null;
    }

    _guardBody() {
      this._body.inert = this._posting || this._saving;
    }

    _lockDialog(locked) {
      this._saving = locked;
      for (const button of this.element.querySelectorAll("button")) {
        button.disabled = locked;
      }
      this._guardBody();
    }

    _focusError() {
      const wrong = this._body.querySelector(
        ".lab-field--error :is(input, select, textarea)");
      if (wrong) wrong.focus();
    }

    _focusAfterSave() {
      if (!this._openerInPopover && this._opener && this._opener.isConnected
          && this._opener.getAttribute("href") === this._openerHref) {
        this._opener.focus({ preventScroll: true });
        return;
      }
      const titleId = this._openerPane === "lot-detail"
        ? "lot-detail-title" : "item-detail-title";
      const heading = document.getElementById(titleId)
        || document.getElementById("item-detail-title")
        || document.querySelector("main h1");
      if (!heading) return;
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    }

    _masterDetailControllers() {
      const found = [];
      for (const el of document.querySelectorAll("[data-controller]")) {
        const ctrl = this.application.getControllerForElementAndIdentifier(
          el, "master-detail");
        if (ctrl) found.push(ctrl);
      }
      return found;
    }

    _widgetKey(body) {
      const widget = body.closest(".widget");
      if (!widget) return "";
      if (widget.id) return widget.id;
      const pane = widget.closest("aside[id]");
      const head = widget.querySelector(".widget__head :is(h2, h3)");
      return head ? `${pane?.id || ""}:${head.textContent.trim()}` : "";
    }

    async _refreshPage() {
      const beforeCtrls = this._masterDetailControllers();
      let address = location.href;
      if (beforeCtrls.length) {
        let search = location.search;
        for (const ctrl of beforeCtrls) {
          const item = paneItemOf(ctrl.paneValue);
          if (item) search = paramSearch(search, ctrl.paramValue, item);
        }
        address = `${location.pathname}${search}`;
      }
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
        const part = box.querySelector("table[id], tbody[id]");
        const id = box.id || part?.id;
        if (id && (box.scrollTop || box.scrollLeft)) {
          boxScroll.set(id, {
            byBox: Boolean(box.id),
            top: box.scrollTop,
            left: box.scrollLeft,
          });
        }
      }
      const widgetScroll = new Map();
      for (const body of document.querySelectorAll(".widget__body")) {
        const key = this._widgetKey(body);
        if (key && (body.scrollTop || body.scrollLeft)) {
          widgetScroll.set(key, {
            top: body.scrollTop,
            left: body.scrollLeft,
          });
        }
      }
      for (const node of refreshParts(fresh)) {
        htmx.process(node);
        enhanceSortable(node);
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
      for (const body of document.querySelectorAll(".widget__body")) {
        const pos = widgetScroll.get(this._widgetKey(body));
        if (pos) {
          body.scrollTop = pos.top;
          body.scrollLeft = pos.left;
        }
      }
      const afterCtrls = this._masterDetailControllers();
      if (afterCtrls.length) {
        for (const ctrl of afterCtrls) {
          ctrl.restoreAfterRefresh(ticked);
        }
      } else {
        for (const box of document.querySelectorAll("input[name=item]")) {
          box.checked = ticked.has(box.value);
        }
      }
    }
  }

  // A back link returns through history when this page was opened from
  // a page of the list it leads to, so the list keeps its state. The
  // page marks the history entry it loaded in; from a later entry of the
  // same page, such as one a skip link added, the link is followed.
  if (document.querySelector("a[data-back]")) {
    try {
      history.replaceState({ ...(history.state || {}), backEntry: true }, "");
    } catch {
      // History state unavailable: the links are followed.
    }
  }
  document.addEventListener("click", (event) => {
    if (!plain(event) || !(event.target instanceof Element)) return;
    const link = event.target.closest("a[data-back]");
    if (!link || history.length < 2 || !document.referrer) return;
    if (!(history.state && history.state.backEntry)) return;
    let from;
    try {
      from = new URL(document.referrer);
    } catch {
      return;
    }
    if (from.origin !== location.origin
        || from.pathname !== new URL(link.href).pathname) return;
    event.preventDefault();
    history.back();
  });

  const schema = {
    ...Stimulus.defaultSchema,
    actionAttribute: "data-lab-action",
  };
  const application = Stimulus.Application.start(
    document.documentElement, schema);
  application.register("popover-anchor", PopoverAnchorController);
  application.register("batch-narrow", BatchNarrowController);
  application.register("sortable-table", SortableTableController);
  application.register("master-detail", MasterDetailController);
  application.register("dialog", DialogController);
})();
