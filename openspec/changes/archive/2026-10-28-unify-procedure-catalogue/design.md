## Context

The catalogue joins three things that live apart today: the static
procedure table Hugo renders, the Pagefind index the build writes, and
state that a reader shares as a URL. Hugo knows every procedure's
metadata at build time but nothing about a query; Pagefind knows which
pages match a query but identifies them by content hashes; the address
bar has to describe the combination in a form that survives reloads,
Back/Forward and copying.

## Decisions

### Rows are the records

The table Hugo renders is the catalogue's data. Each body row carries the
procedure's ID, title, facet keys and timestamps as data attributes, and
the catalogue script reads its records from those rows. Rendering hides
the rows that do not match and re-appends the rest in the chosen order;
the script generates no row markup. The Details view's extra fields are
also static markup inside each row, shown by a stylesheet rule.

- *Rejected: a generated JSON catalogue.* A second copy of the metadata
  would need a separate generator and could drift from the table that the
  no-JavaScript reader sees.
- *Rejected: rendering rows in JavaScript.* It duplicates the
  `procedure-table` partial and loses the static fallback.

### Facets are computed in the page, not by Pagefind

Facet matching, counts and sorting run in the catalogue's core functions
over the records. Pagefind contributes only the set of IDs that match the
text query and their relevance order. Filter-only browsing therefore
never loads the index, and works when the index is missing.

- *Rejected: Pagefind filters for the facets.* Pagefind's filter values
  are the display labels it indexed (localized), not machine values;
  counts that leave out a facet's own selections would need a search per
  facet; and the term-page scope would be a fourth mechanism. The four
  label filters lose their only consumer and are removed.

### Mapping Pagefind results to procedures

A Pagefind result names its page by a hash. Each procedure page gives
Pagefind its ID twice, on the header element that already carries the
`id` meta field: as the filter `id` and as the sort key `id`. Once per
page view the catalogue's searcher calls `filters()`, which loads the
filter index and lists every indexed ID, and runs one filter-only search
sorted by `id`, which lists every page hash in ID order. IDs are
`OSDB-` and four digits, so their code-point order is Pagefind's sort
order, and pairing the two sorted lists maps each hash to its ID. Every
query is then one plain search whose hashes are looked up in that map,
which keeps Pagefind's relevance order. A count mismatch, or a hash
missing from the map, is an index error, never a guess.

- *Rejected: `result.data().meta.id`.* Each call loads the page's
  fragment, which holds the page's full text, so a broad query would load
  every procedure body to learn IDs the page already has.
- *Rejected: a filter-only search per ID.* Correct, but one search per
  procedure on every page view.
- *Rejected: joining on the title.* Titles are not unique and differ
  between languages.

### Pagefind is loaded on demand, relative to the script

The catalogue imports `pagefind.js` only when a query is active, from the
URL `../pagefind/pagefind.js` resolved against its own script URL, which
Hugo's `relativeURLs` already makes correct under any path prefix.
Pagefind derives its base path from the module's URL, so the index,
worker and WebAssembly load from the same directory at `/` and at
`/orgsyndb/`.

### The address

The state is `q`, the selected values of the four facets, an explicit
sort or none, and the view. It is written as `q`, repeated `type`,
`status`, `tag` and `author`, `sort` and `view` in that order, facet
values in the order the page lists them, and nothing for a default.
Parsing the same address always gives the same state and the same list
of ignored parameters.

- **Machine values.** Reaction types use their vocabulary slug, status
  its literal, tags and authors their key in Hugo's taxonomy: the term as
  written, lowercased (`a. example` for `A. Example`). Keys may contain
  spaces, so rows carry them as JSON arrays and the address encodes them
  as `URLSearchParams` does (`author=a.+example`). Author keys are only as
  stable as the names written in the procedures of one build; the address
  promises nothing across builds or languages.
  *Rejected: the term page's path segment (`a.-example`).* It has no
  spaces, but it is a second spelling of the key, not the key itself.
- **What cannot be applied is dropped and reported.** A value the page
  does not know, a fixed facet's parameter on a term page, a repeated `q`,
  `sort` or `view`, a `sort` that does not apply, an unknown `view`, and
  any other parameter name are ignored. The page names them in a notice
  and replaces the history entry with the canonical address, so it never
  shows a filter as active that it did not apply.
  *Rejected: applying unknown values as filters that match nothing.* It
  is consistent, but the page could only label the selection with its raw
  key, and a stale shared link would silently empty the list.
- **Known values.** Every catalogue page lists, and so knows, every value
  in use in the collection, and the three status literals; a term page
  knows no value of its fixed facet. A selected value that no row in the
  scope carries counts 0 and stays shown and removable, and Browse all
  carries it on. Unselected values with a zero count are hidden, so a
  term page shows only the values of its rows until one is selected.
  *Rejected: knowing only the values of the page's own rows.* A valid
  author outside a tag's scope would be dropped as unknown and lost on the
  way to `/procedures/`.

### Sort

`sort` absent means the default: relevance while the query is active,
ID otherwise. A chosen sort is kept across query changes, except that a
chosen relevance is dropped once the query is no longer active, so the
order falls back to ID and the address loses `sort=relevance`. A query is
active when `normaliseTerm` leaves it non-empty, the same rule Pagefind
searching uses.

### History

A run of edits in the search field creates one history entry: its first
debounced change pushes an entry, the later ones replace it. The run ends
when the field loses focus, on Enter, or with any other change. Every
other change (facet, chip, Clear all, sort, view, the error action)
pushes an entry. Back and Forward re-read the address and render it.
Each render takes a sequence number, and a search result is used only if
its render is still the latest, so a slow search never overwrites a newer
state.

### Static fallback

Without JavaScript, the catalogue and term pages show their full table by
ID and a `noscript` note that search, filters and sorting need
JavaScript, with links to the three directories. All catalogue controls
sit in containers marked `hidden` that only the script reveals, so no
inactive control is shown. The header search form works without
JavaScript and submits to `/procedures/?q=…`, whose fallback is that same
full list and note; the note never claims a query or filter was applied.

### Index errors

When the index cannot be loaded or a search fails while a query is
active, the catalogue shows no rows, hides facet counts, says that the
search was not applied and offers a button that removes the query.
Removing it returns to filter-only browsing, which needs no index. While a
search is pending, the results region is marked busy and the count reads
"Searching…", so earlier rows are not presented as the new query's
matches.

### Page layout

- **Facets.** On wide windows the facets form a sidebar beside the
  results; below 55rem they collapse behind a Filters toggle with
  `aria-expanded`. Each facet is a native `details` group, open for
  reaction type and status and closed for tag and author unless one of
  their values is selected, which keeps long lists collapsible without a
  custom widget. Unselected values with a zero count are hidden, selected
  ones always shown.
- **Details view.** The Details fields sit in a block inside the
  Procedure cell rather than in extra columns or extra rows: the table
  keeps one row per procedure and five columns, nothing needs a column
  manager, and narrow windows wrap the block instead of widening the
  table. Images load lazily and appear only where `structure_image` is
  set; there is no placeholder.
- **Navigation.** Tags and authors leave the main menu but remain
  facets of the catalogue, so their directories and term pages count as
  part of the Procedures section for `aria-current`; reaction-type term
  pages stay in Reaction types.

## Risks and trade-offs

- The ID mapping relies on Pagefind's string sort agreeing with
  code-point order for fixed-width IDs. The schema guarantees the width,
  and the real-index tests compare the mapping with `meta.id` for every
  findability query.
- A shared address with an author key from a differently translated
  build is reported as ignored rather than translated.
- Facet counts are computed over all rows on every change; with the
  collection sizes the site is built for, this is far below the cost of a
  Pagefind search.
