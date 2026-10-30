## 1. Tests and fixtures, red first

- [x] 1.1 General baseline `tests/fixtures/general/OSDB-0140-general.md`
  and its compounds in the fixture registry; the general variant run
- [x] 1.2 Validator: scope entries and their messages, top-level
  `products` refused, `scheme_image`, variants sharing `scope` and
  `scheme_image`
- [x] 1.3 Export: `tests/fixtures/export/OSDB-0909-scope-table.org`, the
  exported `scope`, the body without the table; ERT cases for the
  malformed tables
- [x] 1.4 Test collection: OSDB-0009 and its German variant, the three
  new compounds and the scheme image, as the demo will hold them
- [x] 1.5 Samples: the demo general procedure, counts, chains, German
  twins, quantities
- [x] 1.6 Site: scope table, key facts range, scheme figure and the
  placeholder, compound page entries, `data-kind`, the `kind` facet and
  its address, `/general-procedures/` with its tab, scope line, header
  search and script, the new counts; German strings
- [x] 1.7 Catalogue scripts: `kind` in `parse`, `serialize` and `select`

## 2. Implementation

- [x] 2.1 `tools/validate.py`: `scope`, its entries, `scheme_image`,
  variants
- [x] 2.2 `tools/osdb-org.el` and `tools/export.el`: read the table named
  `scope`, report its problems, write `scope`, drop the table from the
  body
- [x] 2.3 Site: the scope-table partial, products and substrates over
  every entry, key facts, structure slot, compound pages, catalogue rows
  and facet, `/general-procedures/`, tabs, header, i18n, styles;
  `catalogue-core.js` and `catalogue.js`
- [x] 2.4 Demo collection: OSDB-0009 in both languages, its compounds
  and scheme image

## 3. Verification

- [x] 3.1 Full suite: 581 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: OSDB-0009 with its scope table and scheme, the
  compound page of `1-biphenyl-4-yl-ethanol`, `/general-procedures/` and
  the `kind` facet on `/procedures/`, at 1280 and 500 CSS pixels, light
  and dark; the CAS numbers of the new compounds against PubChem; the
  chemistry of OSDB-0009. Checked in headless Firefox on the German demo build:
  OSDB-0009 shows its scheme, the yield range 85–90 %, the scope table
  before the summary with links and only the columns its entries set,
  and, at 500 in the dark scheme, the panel, then the table scrolling in
  its region; the compound page of 1-(biphenyl-4-yl)ethanol lists
  OSDB-0005 and entry 1 of OSDB-0009; `/general-procedures/` lists
  OSDB-0009 with the fixed kind facet. The three CAS numbers resolve on
  PubChem to the named compounds; the reduction is a textbook
  teaching-laboratory procedure with sound hazards

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA*.md`,
  `docs/AUTHORING*.md`, `docs/AUTHORING-ORG*.org`
- [x] 4.2 Codex reviewer: no actionable defects
- [x] 4.3 Archive
