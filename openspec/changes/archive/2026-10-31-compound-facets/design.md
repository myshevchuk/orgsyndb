## Context

`catalogue-core.js` is pure and tested under Node; `catalogue.js` binds
it to a page. Both name the facets `type`, `kind`, `status`, `tag` and
`author` in a constant, and the core's state is a flat object with one
key per facet. The compound directory is a static table built from
`site.Data.compounds` and the staged field data. Compound pages are
deliberately left out of the Pagefind index, so that the procedure
catalogue's results and counts hold procedures only. The next change
divides the compound directory into tabs by one field, which will use
the catalogue's fixed facet as the term pages do.

## Decisions

- **The page names the facets.** A state keeps its flat shape; its
  facets are its keys other than `q`, `sort` and `view`, in key order,
  and `parse` builds them from `known`, which the page fills from its
  facet checkboxes. The procedure catalogues pass the same five facets
  in the same order, so their addresses and behaviour do not change,
  and the field keys that would collide with a state key or a row
  attribute become reserved.
- **The page names its sorts and views.** `parse` keeps only a sort or
  view the page offers. The compound catalogue offers none: its table
  has one natural order, by shown name, and nothing to show in a
  Details view.
- **No chosen sort keeps the page's order.** `select` returns records in
  the order given while no sort is chosen and no query is active. On a
  procedure catalogue that order is by ID, as before; on the compound
  catalogue it is Hugo's order by shown name, so the script never
  reorders the table it was given.
- **Levels are flattened at build time.** A row's facet attribute lists
  the values a compound sets and all their ancestors. Ticking a value
  then selects every compound filed at or below it, and its count
  counts them, with no notion of a tree in the core. The facet lists
  the tree in vocabulary order, depth first, indented by depth, because
  a classification's order is usually chosen with care.
- **Compounds are searched in the page.** The directory already holds
  every compound, so `match` compares the query's words with each row's
  text as substrings, normalised as Pagefind queries are. A SMILES or
  CAS fragment matches without a suffix index, and the procedure
  index stays free of compounds. It has no ranking, so results keep
  the table's order.
- **Which fields filter and which are searched.** Only a `choice` or a
  `boolean` has a closed set of values to tick; only `text` is worth
  searching. The built-in names, formula, CAS number and SMILES are
  always searched, both names in either language.
- **Field data carries ancestor keys and an order.** The layouts cannot
  walk a hierarchy or sort a map in a chosen order, so the pipeline
  stages both.

## Alternatives rejected

- **A separate compound script.** Simpler at first, but two catalogues
  would drift apart in address handling, chips, history and focus.
- **A state with a nested `facets` object.** Cleaner in isolation, but it
  would rewrite every core test and the procedure catalogue for no
  change in behaviour.
- **Compound pages in the Pagefind index, separated by a filter.** The
  procedure search would have to exclude them everywhere, and substring
  search on SMILES would need a second suffix index.
- **The tree expanded in the browser.** The script would need the
  vocabulary as data and the core a notion of descendants; flattening
  in the layout gives the same selections with neither.
- **Facet values ordered by label.** Usual for the procedure facets,
  whose terms have no order of their own, but it would scatter a
  classification's levels.
