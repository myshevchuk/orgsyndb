## 1. Tests and fixtures, red first

- [x] 1.1 Validator: `facet` and `search` where the types take them and
  refused elsewhere; the reserved keys; the unknown-option scenario on
  `tabs`
- [x] 1.2 Field data: `facet`, `search`, `ancestors`, `order`, and the
  depth-first order of a vocabulary listed out of order
- [x] 1.3 Catalogue core under Node: nine functions; facets named by the
  page; offered sorts and views; the order of the records; `match`
- [x] 1.4 Test collection: `facet` and `search` in its `orgsyndb.toml`,
  as the demo will hold them; the demo's declarations
- [x] 1.5 Site: the compound catalogue's elements, facets, values,
  depths and row attributes; a collection without facet fields; the
  header search on `/compounds/` in both languages; the script on
  `/compounds/`; the German strings

## 2. Implementation

- [x] 2.1 `tools/validate.py` and `tools/pipeline.py`: options, reserved
  keys, field data
- [x] 2.2 `site/assets/js/catalogue-core.js`: page facets, offers,
  record order, `match`
- [x] 2.3 `site/assets/js/catalogue.js`: facets, records and offers from
  the page, text search, optional selects and toggle
- [x] 2.4 Site: the compound catalogue layout, the header search, the
  script partial, the facet indentation, i18n strings
- [x] 2.5 Demo collection: `orgsyndb.toml` as the test collection's

## 3. Verification

- [x] 3.1 Full suite: 849 passed and 1 skipped (`caddy`), before the
  reviewer's fix and its style test
- [x] 3.2 Browser: site-catalogue "Filtering and searching compounds" on
  the German demo build, light and dark, at 1280 and 500 CSS pixels;
  and, on the procedure catalogue and a term page, the scenarios of
  "Catalogue in a browser" and "Fixed scope on term pages": searching
  and filtering together, the address, a slow search, the keyboard and
  the index error. Driven through Marionette in headless Firefox on the
  German demo build: the compound walk narrowed 20 → 15 → 7 → 1 rows
  with counts, chips and addresses as stated, the reload, chip removal
  and Back gave the stated addresses, and the bad address showed the
  notice for both parameters; the narrow layout's Filters button
  toggled. On the procedure side the search with a status filter, the
  restored address with the Details view, the ignored parameters, a
  first search delayed past a newer query, chip and Clear all focus,
  the term page's scope and Browse all link, and the index error with
  its button all behaved as before. Tab order and focus outlines were
  not re-checked: neither the procedure controls' markup nor the focus
  styles changed. Beside the facets the compound table overflowed and
  broke names mid-word; long words in it now hyphenate and its header
  cells wrap

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA.md`,
  `docs/SCHEMA.de.md`, and the sentence introducing `/compounds/` in the
  four authoring guides
- [x] 4.2 Codex reviewer: one finding, the results of a catalogue
  without facets fell into the facet column; fixed with a style test
- [x] 4.3 Archive
