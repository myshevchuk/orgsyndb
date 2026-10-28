// The catalogue on /procedures/ and the term pages, as a progressive
// enhancement: without it the page is its full table by ID. It runs after
// search-terms.js and catalogue-core.js, in one bundle.
//
// - Reveals every [data-catalogue-controls] element of div.catalogue, and
//   drives the search field #catalogue-q of the site header's form.
// - Reads its records from the table rows, its known facet values from the
//   facet checkboxes and its fixed facet from data-fixed, and its state
//   from the address with OrgSynCatalogue.parse. Parameters it could not
//   apply are named in the message, and the address is replaced with the
//   canonical one.
// - On each change of state it renders: hides the rows that do not match,
//   re-appends the others in order, fills the facet counts, the chips, the
//   count and the message, and sets the controls. Only the latest render
//   applies a search result.
// - Imports the Pagefind bundle, ../pagefind/pagefind.js resolved against
//   this script's URL, only while the query is active, and runs each
//   distinct normalised query once per page view.
// - Typing changes the query 250 ms after the last keystroke; a run of
//   edits makes one history entry. Every other change pushes one. Back and
//   Forward render the address they reach.
// - Below 55rem the Filters button shows and hides the facets.
(() => {
  "use strict";

  // Set only while this script runs, so read it before anything else.
  const scriptURL = document.currentScript ? document.currentScript.src : "";
  const core = globalThis.OrgSynCatalogue;
  const root = document.querySelector("[data-catalogue]");
  if (!root || !core) return;

  const FACETS = ["type", "status", "tag", "author"];
  const DELAY = 250;
  const fixed = root.dataset.fixed || null;
  const language = document.documentElement.lang || undefined;
  const text = (name) => root.getAttribute(`data-text-${name}`) || "";
  const fill = (template, values) => template.replace(
    /\{(\w+)\}/g, (all, name) => (name in values ? values[name] : all));

  let numbers;
  try {
    numbers = new Intl.NumberFormat(language);
  } catch {
    numbers = new Intl.NumberFormat();
  }
  const format = (n) => numbers.format(n);

  const field = document.getElementById("catalogue-q");
  const form = field && field.form;
  if (!form) return;
  const results = root.querySelector(".catalogue-results");
  const toggle = root.querySelector(".facets-toggle");
  const chips = root.querySelector(".catalogue-active");
  const clearAll = root.querySelector(".clear-all");
  const sortSelect = root.querySelector("#catalogue-sort");
  const viewSelect = root.querySelector("#catalogue-view");
  const relevance = sortSelect.querySelector('option[value="relevance"]');
  const message = root.querySelector("[data-catalogue-message]");
  const count = root.querySelector("[data-catalogue-count]");
  const countText = count.textContent;
  const browseAll = root.querySelector("[data-browse-all]");
  const browseURL = browseAll ? new URL(browseAll.href) : null;
  const body = root.querySelector("table.procedure-list tbody");

  // --- records and facet values ------------------------------------------

  const keysOf = (row, name) => {
    try {
      const value = JSON.parse(row.dataset[name] || "[]");
      return Array.isArray(value) ? value : [];
    } catch {
      return [];
    }
  };
  const rows = new Map();
  const records = [];
  for (const row of body.rows) {
    const id = row.dataset.id;
    if (!id || rows.has(id)) continue;
    rows.set(id, row);
    records.push({
      id,
      title: row.dataset.title || "",
      created: row.dataset.created || "",
      modified: row.dataset.modified || "",
      type: keysOf(row, "type"),
      status: row.dataset.status ? [row.dataset.status] : [],
      tag: keysOf(row, "tag"),
      author: keysOf(row, "author"),
    });
  }

  // Per facet: its name and, per value, the checkbox, its label element,
  // its count element and its display label.
  const groups = {};
  for (const details of root.querySelectorAll("details.facet[data-facet]")) {
    const summary = details.querySelector("summary");
    groups[details.dataset.facet] = {
      details,
      name: summary ? summary.textContent.trim() : details.dataset.facet,
      values: Array.from(details.querySelectorAll("label.facet-value"),
        (label) => {
          const input = label.querySelector("input");
          const shown = label.querySelector(".facet-label");
          return {
            input,
            label,
            value: input.value,
            count: label.querySelector(".facet-count"),
            text: shown ? shown.textContent.trim() : input.value,
          };
        }),
    };
  }
  const known = {};
  for (const facet of FACETS) {
    const group = groups[facet];
    known[facet] = facet === fixed || !group ? []
      : Array.from(new Set(group.values.map((item) => item.value)));
  }
  const labelOf = (facet, value) => {
    const item = groups[facet].values.find((entry) => entry.value === value);
    return item ? item.text : value;
  };

  // --- state and history -------------------------------------------------

  let state = null;
  let notice = "";
  let typing = null;
  let runEntry = false;

  const filtering = () => state.q.trim() !== ""
    || FACETS.some((facet) => state[facet].length > 0);

  // Reads the state from the address, names what it ignored and makes the
  // address canonical.
  const fromAddress = () => {
    const read = core.parse(location.search, known, fixed);
    state = read.state;
    notice = read.ignored.length === 0 ? "" : fill(text("ignored"), {
      list: read.ignored.map(([name, value]) => `${name}=${value}`)
        .join(", "),
    });
    const canonical = core.serialize(state);
    if (canonical !== location.search) {
      history.replaceState(null, "", location.pathname + canonical
        + location.hash);
    }
  };

  // Makes NEXT the state, records it in the history as HOW ("push" or
  // "replace") when its address differs, and renders it.
  const apply = (next, how, setField) => {
    const before = core.serialize(state);
    const after = core.serialize(next);
    state = next;
    notice = "";
    if (after !== before) {
      history[how === "replace" ? "replaceState" : "pushState"](
        null, "", location.pathname + after);
    }
    render(setField);
    return after !== before;
  };

  // Applies the search field as the query, as part of the run of edits.
  const typed = () => {
    typing = null;
    const how = runEntry ? "replace" : "push";
    if (apply(core.withQuery(state, field.value), how, false)) {
      runEntry = true;
    }
  };

  const endRun = () => {
    if (typing !== null) {
      window.clearTimeout(typing);
      typed();
    }
    runEntry = false;
  };

  // Applies a deliberate change as a new history entry. BUILD makes the
  // next state from the current one once a pending edit of the search
  // field has been applied, so that the edit is kept; a handler reads its
  // control before calling this, since that flush re-renders the controls.
  const change = (build, setField) => {
    endRun();
    apply(build(state), "push", setField);
  };

  const without = (current, facet, value) => Object.assign({}, current, {
    [facet]: current[facet].filter((v) => v !== value),
  });

  // --- searching ---------------------------------------------------------

  let loading = null;
  const searches = new Map();

  const loadSearcher = () => {
    if (loading === null) {
      loading = Promise.resolve()
        .then(() => import(new URL("../pagefind/pagefind.js", scriptURL).href))
        .then((pagefind) => core.searcher(pagefind));
      loading.catch(() => {
        loading = null;
      });
    }
    return loading;
  };

  const search = (q) => {
    const key = globalThis.OrgSynSearch.normaliseTerm(q);
    let found = searches.get(key);
    if (!found) {
      found = loadSearcher().then((searcher) => searcher.search(key));
      searches.set(key, found);
      found.catch(() => {
        if (searches.get(key) === found) searches.delete(key);
      });
    }
    return found;
  };

  // --- rendering ---------------------------------------------------------

  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "catalogue-retry";
  retry.textContent = text("error-action");

  let shownMessage = null;
  let shownChips = null;
  const setMessage = (parts, button) => {
    const texts = parts.filter(Boolean);
    const key = JSON.stringify([texts, Boolean(button)]);
    if (key === shownMessage) return;
    shownMessage = key;
    message.replaceChildren();
    texts.forEach((part, i) => message.append(i ? " " : "", part));
    if (button) message.append(" ", button);
    message.hidden = texts.length === 0 && !button;
  };

  const syncControls = (setField) => {
    if (setField) field.value = state.q;
    const chosen = [];
    for (const facet of FACETS) {
      const group = groups[facet];
      if (!group) continue;
      for (const item of group.values) {
        if (facet === fixed) {
          item.input.checked = true;
          item.input.disabled = true;
        } else {
          item.input.checked = state[facet].includes(item.value);
        }
      }
      if (facet === fixed) continue;
      if ((facet === "tag" || facet === "author") && state[facet].length) {
        group.details.open = true;
      }
      for (const value of state[facet]) chosen.push([facet, value]);
    }
    if (core.active(state)) {
      if (!relevance.parentNode) sortSelect.prepend(relevance);
    } else {
      relevance.remove();
    }
    sortSelect.value = core.sortOf(state);
    viewSelect.value = state.view;
    root.dataset.view = state.view;

    // Rebuilt only when the selections change: a query edit applied as the
    // field loses focus to a chip must not replace the chip being clicked.
    const chipKey = JSON.stringify(chosen);
    if (chipKey !== shownChips) {
      shownChips = chipKey;
      chips.replaceChildren(...chosen.map(([facet, value], index) => {
      const name = groups[facet].name;
      const label = labelOf(facet, value);
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = `${name}: ${label}`;
        button.setAttribute("aria-label",
          fill(text("remove"), { facet: name, value: label }));
        button.addEventListener("click", () => {
          change((current) => without(current, facet, value), false);
          const left = chips.querySelectorAll("button");
          (left[index] || left[index - 1] || field).focus();
        });
        const item = document.createElement("li");
        item.append(button);
        return item;
      }));
    }
    chips.hidden = chosen.length === 0;
    clearAll.hidden = !filtering();
    if (browseURL) {
      browseURL.search = core.serialize(state);
      browseAll.href = browseURL.href;
    }
  };

  const show = ({ ids, counts }) => {
    results.removeAttribute("aria-busy");
    const displayed = new Set(ids);
    // Moving a row takes the focus from a link in it, so rows move only
    // when their order changes, and a focused link still shown gets its
    // focus back.
    const focused = body.contains(document.activeElement)
      ? document.activeElement : null;
    for (const [id, row] of rows) row.hidden = !displayed.has(id);
    const order = Array.from(body.rows, (row) => row.dataset.id)
      .filter((id) => displayed.has(id));
    if (order.join(" ") !== ids.join(" ")) {
      for (const id of ids) body.append(rows.get(id));
      if (focused && !focused.closest("[hidden]")) {
        focused.focus({ preventScroll: true });
      }
    }
    for (const facet of FACETS) {
      const group = groups[facet];
      if (!group) continue;
      for (const item of group.values) {
        const n = facet === fixed ? ids.length
          : (counts[facet] && counts[facet][item.value]) || 0;
        item.count.textContent = format(n);
        item.count.hidden = false;
        item.label.hidden = facet !== fixed && n === 0
          && !state[facet].includes(item.value);
      }
    }
    count.textContent = filtering()
      ? fill(count.dataset.filtered,
        { shown: format(ids.length), total: format(rows.size) })
      : countText;
    setMessage([notice, ids.length === 0 ? text("empty") : ""], null);
  };

  const failed = () => {
    results.removeAttribute("aria-busy");
    for (const row of rows.values()) row.hidden = true;
    for (const group of Object.values(groups)) {
      for (const item of group.values) {
        item.count.hidden = true;
        item.label.hidden = false;
      }
    }
    count.textContent = text("unavailable");
    setMessage([notice, text("error")], retry);
  };

  let latest = 0;
  const render = (setField) => {
    const turn = ++latest;
    syncControls(setField);
    if (!core.active(state)) {
      show(core.select(records, state, null, language));
      return;
    }
    results.setAttribute("aria-busy", "true");
    count.textContent = text("searching");
    setMessage([notice], null);
    // No search result can show a row outside the selected facets, so
    // such rows go at once rather than when the search answers.
    const possible = new Set(core.select(records, state, null, language).ids);
    for (const [id, row] of rows) if (!possible.has(id)) row.hidden = true;
    search(state.q).then((ids) => {
      if (turn === latest) show(core.select(records, state, ids, language));
    }, () => {
      if (turn === latest) failed();
    });
  };

  // --- events ------------------------------------------------------------

  field.addEventListener("input", () => {
    window.clearTimeout(typing);
    typing = window.setTimeout(typed, DELAY);
  });
  field.addEventListener("blur", endRun);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    window.clearTimeout(typing);
    typed();
    runEntry = false;
  });

  for (const facet of FACETS) {
    if (facet === fixed || !groups[facet]) continue;
    for (const item of groups[facet].values) {
      item.input.addEventListener("change", () => {
        const on = item.input.checked;
        change((current) => Object.assign({}, current, {
          [facet]: known[facet].filter((value) => (value === item.value
            ? on : current[facet].includes(value))),
        }), false);
      });
    }
  }

  clearAll.addEventListener("click", () => {
    change(core.clear, true);
    field.focus();
  });
  retry.addEventListener("click", () => {
    change((current) => core.withQuery(current, ""), true);
    field.focus();
  });
  sortSelect.addEventListener("change", () => {
    const sort = sortSelect.value;
    change((current) => Object.assign({}, current, { sort }), false);
  });
  viewSelect.addEventListener("change", () => {
    const view = viewSelect.value;
    change((current) => Object.assign({}, current, { view }), false);
  });
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    root.toggleAttribute("data-facets-open", open);
  });

  window.addEventListener("popstate", () => {
    window.clearTimeout(typing);
    typing = null;
    runEntry = false;
    fromAddress();
    render(true);
  });

  for (const element of root.querySelectorAll("[data-catalogue-controls]")) {
    element.hidden = false;
  }
  fromAddress();
  render(true);
})();
