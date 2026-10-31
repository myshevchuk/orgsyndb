## 1. Tests and fixtures, red first

- [x] 1.1 Validator: `tabs` on a choice field, two tabs fields, tabs on
  another type, the unknown-option scenario on `sortable`, a compound
  named like the tabs field
- [x] 1.2 Field data: `tabs`
- [x] 1.3 Test collection: the `group` field, `inventory-groups.toml`
  and every compound's `group`, as the demo will hold them; the demo's
  declarations, vocabularies and values
- [x] 1.4 Site: the compound tabs on `/compounds/` and the tab pages,
  the tab pages' rows, titles, counts, facets and header search, in
  both languages; no tabs without a tabs field; the script on tab
  pages; the page shell and navigation on tab pages

## 2. Implementation

- [x] 2.1 `tools/validate.py` and `tools/pipeline.py`: the option, its
  errors, the tab-path rule, the field data
- [x] 2.2 Site: tab pages from the compound content adapter, their
  layout, the compound tabs partial, the header search, i18n strings
- [x] 2.3 Demo collection: `orgsyndb.toml`, `vocabularies/` and the
  compounds, as the test collection's

## 3. Verification

- [x] 3.1 Full suite: 896 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: site-catalogue "Filtering within a tab" on the German
  demo build, light and dark, at 1280 and 500 CSS pixels. Driven through
  Marionette in headless Firefox: Zugekauft opened with its ten
  compounds and its own tab marked, Reagenzien narrowed them to four
  and `acet` to three, the tab Alle Verbindungen opened every compound
  with its own tab marked, and Back restored the tab page's address,
  rows and chip. The Gruppe facet of Zugekauft lists Ausgangsstoffe and
  Reagenzien at the top level; the tabs take the procedure tabs' look

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA.md`,
  `docs/SCHEMA.de.md`, and the demo's required fields in the four
  authoring guides
- [x] 4.2 Codex reviewer: no actionable defects
- [x] 4.3 Archive
