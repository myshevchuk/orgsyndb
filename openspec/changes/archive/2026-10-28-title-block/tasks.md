## 1. Tests, red first

- [x] 1.1 Procedure page order: the key facts and the structure figure in
  the header, the article without the figure
- [x] 1.2 Key facts and sign-off, with the catalogue fixtures for a
  checked procedure
- [x] 1.3 Metadata panel without `Scale`, `Yield`, and `Checked by` for a
  checked procedure; the structure slot in the header
- [x] 1.4 Narrow windows: `.procedure-header` `display: block` (the
  stylesheet already declared it; the test states it)
- [x] 1.5 German panel and key facts

## 2. Implementation

- [x] 2.1 `procedure-header.html`, a `key-facts.html` partial,
  `procedure-meta.html`, `procedures/page.html`; the sign-off string
- [x] 2.2 `screen.css`: the title block's columns and closing rule, the
  structure in the header; `base.css`: the key facts, the badge in normal
  case

## 3. Verification

- [x] 3.1 Full suite: 399 passed and 1 skipped (`caddy`) with Node
- [x] 3.2 Browser: procedure pages with and without a structure image,
  light and dark, at 1440, 1000 and 500 CSS pixels; a printed page.
  Checked in headless Firefox on the German demo build: at 1440 and 1000
  OSDB-0003's drawing stands at the right of the ID line, title, key
  facts and button, in the margin's column, with the text rows together
  and the closing rule beneath; OSDB-0004 shows the quiet placeholder
  there; at 500 the drawing follows the button, with no doubled rule
  before the details; the dark scheme blends the drawing into the page.
  WeasyPrint's page 1 of OSDB-0003 reads banner, ID line, title, key
  facts, URL facts, drawing, the boxed panel, then the body

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md` and the authoring guides
- [x] 4.2 Codex reviewer: no findings; all 17 scenarios implemented
- [x] 4.3 Archive
