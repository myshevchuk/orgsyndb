// The catalogue's pure logic, as a classic script (no import or export)
// that defines globalThis.OrgSynCatalogue and touches no page. It needs
// globalThis.OrgSynSearch from search-terms.js, loaded before it; the
// catalogue script bundles both, and the tests load them under Node.
//
// A state is {q, type, kind, status, tag, author, sort, view}: q a
// string, the five facets arrays of machine values, sort null or one of
// SORTS, view "table" or "details". A record is {id, title, created,
// modified, type, kind, status, tag, author}, with RFC 3339 timestamps and
// the facets' values (kind and status may be a single string). No function changes its arguments.
//
// parse(search, known, fixed): {state, ignored} of a query string. known
//   maps each facet to the values the page knows, in the page's order;
//   fixed is the facet a term page or the general procedures' page
//   fixes, or null. ignored lists the
//   [name, value] pairs not applied, in address order.
// serialize(state): the canonical query string, "" for the default state.
// active(state): whether the query leaves a term after normalisation.
// sortOf(state): the sort in effect.
// withQuery(state, q): the state with the query q, dropping a chosen
//   relevance sort that q no longer supports.
// clear(state): the state Clear all leaves: no query, no selection, the
//   view and a sort other than relevance kept.
// select(records, state, matched, language): {ids, counts}. matched is
//   null without an active query, else the IDs matching it in relevance
//   order. ids are the displayed records in the order of the sort in
//   effect; counts[facet][value] counts the records that match the query,
//   carry the value and match every other facet.
// searcher(pagefind): {search(q)}, a promise of the IDs of the procedure
//   pages Pagefind finds for q, in result order. It pairs Pagefind's page
//   hashes with procedure IDs through the id filter and sort key, once,
//   and rejects with an Error when the index does not pair up.
(function () {
  "use strict";

  const FACETS = ["type", "kind", "status", "tag", "author"];
  const SORTS = ["relevance", "id", "title", "created", "modified"];
  const VIEWS = ["table", "details"];

  const byCodePoint = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  const copy = (state) => {
    const out = { q: String(state.q === undefined ? "" : state.q) };
    for (const facet of FACETS) out[facet] = (state[facet] || []).slice();
    out.sort = state.sort === undefined ? null : state.sort;
    out.view = state.view === "details" ? "details" : "table";
    return out;
  };

  const active = (state) =>
    globalThis.OrgSynSearch.normaliseTerm(state.q || "") !== "";

  const parse = (search, known, fixed) => {
    const params = Array.from(new URLSearchParams(search));
    const ignored = [];
    const first = params.find(([name]) => name === "q");
    const state = {
      q: first ? first[1].trim() : "",
      type: [], kind: [], status: [], tag: [], author: [],
      sort: null, view: "table",
    };
    const chosen = Object.fromEntries(FACETS.map((f) => [f, new Set()]));
    const seen = new Set();
    for (const pair of params) {
      const [name, value] = pair;
      if (FACETS.includes(name)) {
        const values = (known && known[name]) || [];
        if (name !== fixed && values.includes(value)) {
          chosen[name].add(value);
        } else {
          ignored.push(pair);
        }
        continue;
      }
      const repeated = seen.has(name);
      seen.add(name);
      if (name === "q" && !repeated) continue;
      if (name === "sort" && !repeated && SORTS.includes(value)
          && (value !== "relevance" || active(state))) {
        state.sort = value;
      } else if (name === "view" && !repeated && VIEWS.includes(value)) {
        state.view = value;
      } else {
        ignored.push(pair);
      }
    }
    for (const facet of FACETS) {
      state[facet] = ((known && known[facet]) || []).filter(
        (value) => chosen[facet].has(value));
    }
    return { state, ignored };
  };

  const serialize = (state) => {
    const params = new URLSearchParams();
    const q = String(state.q || "").trim();
    if (q) params.append("q", q);
    for (const facet of FACETS) {
      for (const value of state[facet] || []) params.append(facet, value);
    }
    if (state.sort !== null && state.sort !== undefined) {
      params.append("sort", state.sort);
    }
    if (state.view === "details") params.append("view", "details");
    const text = params.toString();
    return text ? "?" + text : "";
  };

  const sortOf = (state) => {
    const on = active(state);
    if (state.sort && (state.sort !== "relevance" || on)) return state.sort;
    return on ? "relevance" : "id";
  };

  const withQuery = (state, q) => {
    const out = copy(state);
    out.q = q;
    if (out.sort === "relevance" && !active(out)) out.sort = null;
    return out;
  };

  const clear = (state) => {
    const out = copy(state);
    out.q = "";
    for (const facet of FACETS) out[facet] = [];
    if (out.sort === "relevance") out.sort = null;
    return out;
  };

  // The distinct values of a record's facet.
  const valuesOf = (record, facet) => {
    const value = record[facet];
    if (value === undefined || value === null) return [];
    return Array.from(new Set(Array.isArray(value) ? value : [value]));
  };

  const collator = (language) => {
    try {
      return new Intl.Collator(language || undefined, { numeric: true });
    } catch {
      return new Intl.Collator(undefined, { numeric: true });
    }
  };

  const select = (records, state, matched, language) => {
    const unique = [];
    const byId = new Map();
    for (const record of records) {
      if (byId.has(record.id)) continue;
      byId.set(record.id, record);
      unique.push(record);
    }
    const hits = matched === null ? null : new Set(matched);
    const wanted = Object.fromEntries(
      FACETS.map((f) => [f, new Set(state[f] || [])]));
    const fits = (record, facet) => wanted[facet].size === 0
      || valuesOf(record, facet).some((v) => wanted[facet].has(v));

    const counts = {};
    for (const facet of FACETS) {
      const tally = {};
      for (const record of unique) {
        for (const value of valuesOf(record, facet)) tally[value] = 0;
      }
      for (const value of wanted[facet]) tally[value] = 0;
      counts[facet] = tally;
    }
    const shown = [];
    for (const record of unique) {
      if (hits !== null && !hits.has(record.id)) continue;
      const misses = FACETS.filter((facet) => !fits(record, facet));
      if (misses.length === 0) shown.push(record);
      if (misses.length > 1) continue;
      for (const facet of FACETS) {
        if (misses.length === 1 && misses[0] !== facet) continue;
        for (const value of valuesOf(record, facet)) counts[facet][value] += 1;
      }
    }

    const sort = sortOf(state);
    let ordered;
    if (sort === "relevance" && matched !== null) {
      const keep = new Set(shown.map((record) => record.id));
      ordered = Array.from(new Set(matched)).filter((id) => keep.has(id));
    } else {
      const byIdOrder = (a, b) => byCodePoint(a.id, b.id);
      let compare = byIdOrder;
      if (sort === "title") {
        const words = collator(language);
        compare = (a, b) => words.compare(a.title, b.title) || byIdOrder(a, b);
      } else if (sort === "created" || sort === "modified") {
        compare = (a, b) => Date.parse(b[sort]) - Date.parse(a[sort])
          || byIdOrder(a, b);
      }
      ordered = shown.slice().sort(compare).map((record) => record.id);
    }
    return { ids: ordered, counts };
  };

  const searcher = (pagefind) => {
    let pairing = null;

    // Maps each page hash to its procedure ID: the pages of a search
    // sorted by the id sort key, against the counted id filter values in
    // code-point order.
    const pair = async () => {
      const filters = await pagefind.filters();
      const listed = (filters && filters.id) || {};
      const ids = Object.keys(listed).filter((id) => listed[id] > 0)
        .sort(byCodePoint);
      const sorted = await pagefind.search(null, { sort: { id: "asc" } });
      const pages = (sorted && sorted.results) || [];
      if (pages.length !== ids.length) {
        throw new Error(`The search index lists ${ids.length} procedure IDs `
          + `but ${pages.length} procedure pages.`);
      }
      return new Map(pages.map((page, i) => [page.id, ids[i]]));
    };

    const search = async (q) => {
      const term = globalThis.OrgSynSearch.normaliseTerm(q);
      if (!term) return [];
      if (pairing === null) pairing = pair();
      const current = pairing;
      try {
        const ids = await current;
        const found = await pagefind.search(term);
        const out = [];
        for (const result of (found && found.results) || []) {
          const id = ids.get(result.id);
          if (id === undefined) {
            throw new Error(`The search index returned page ${result.id}, `
              + "which has no procedure ID.");
          }
          if (!out.includes(id)) out.push(id);
        }
        return out;
      } catch (error) {
        if (pairing === current) pairing = null;
        throw error;
      }
    };

    return { search };
  };

  globalThis.OrgSynCatalogue = {
    parse, serialize, active, sortOf, withQuery, clear, select, searcher,
  };
})();
