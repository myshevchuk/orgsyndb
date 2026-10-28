## 1. Tests, red first

- [x] 1.1 Page shell: the header search on every page; on `/procedures/`
  and the term pages its catalogue attributes, action and scoped labels
- [x] 1.2 Catalogue: no search form inside `div.catalogue`; the part order
  without it
- [x] 1.3 German shell and catalogue: the header texts and the term-page
  labels

## 2. Implementation

- [x] 2.1 `site-header.html` and `catalogue.html`; the interface strings
- [x] 2.2 `catalogue.js` finds its field in the header form
- [x] 2.3 Header layout and `h1` size in `screen.css`; the removed
  `.catalogue-search` rules

## 3. Verification

- [x] 3.1 Full suite, with and without Node: 389 passed and 1 skipped
  (`caddy`) with Node; 345 passed and 45 skipped without
- [x] 3.2 Browser: header height and the positions of title, navigation
  and search form equal on the home page, `/procedures/`, a term page, a
  procedure page and a help page at 1280 and 500 CSS pixels, and every
  `h1` the same size; the catalogue browser checks rerun. Checked in
  headless Firefox on six pages: the header is 89 px high at 1280 and
  136 px at 500, title, navigation and form boxes identical on every page
  (the scrollbar gutter is reserved, so short pages match long ones), every
  `h1` 36 px; the 77 catalogue checks and the four review regressions
  pass. The form grows to 30rem where the row has room, so the German
  placeholder `Produkt, CAS, SMILES oder Stichwort` fits from about 920 px
  and the form never wraps above 55rem

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md` "Use the site"
- [x] 4.2 Codex reviewer: no findings; every scenario implemented
- [x] 4.3 Archive
