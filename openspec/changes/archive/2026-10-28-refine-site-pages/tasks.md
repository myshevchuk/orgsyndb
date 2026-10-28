## 1. Tests, red first

- [x] 1.1 `link_notes`: anchors, references, numbering, German, code and
  texts without notes
- [x] 1.2 Page shell: the footer's build time, the same on every page
- [x] 1.3 Home page: the `h1`, the unchecked list, its link and count,
  the four browse entries; no section without drafts
- [x] 1.4 Metadata panel: no `ID`; `Product` only when it differs from
  the title; the index-terms element
- [x] 1.5 Catalogue controls: the term-page placeholder
- [x] 1.6 German strings: footer, status labels, home page, panel labels,
  term-page placeholder
- [x] 1.7 Linked notes on a built procedure page

## 2. Implementation

- [x] 2.1 `pipeline.link_notes` and its use in `stage_content`
- [x] 2.2 Layouts and interface strings
- [x] 2.3 `screen.css`: the home columns and the targeted note

## 3. Verification

- [x] 3.1 Full suite: 395 passed and 1 skipped (`caddy`) with Node
- [x] 3.2 Browser: home page, term-page placeholder, a procedure's panel,
  a note link and its highlight, light and dark, at 1440 and 500 CSS
  pixels. Checked in headless Firefox on the German demo build: the home
  page shows `Noch nicht geprüft` with OSDB-0001 to 0005 and `Alle
  Entwürfe (8)`, Browse spanning both rows beside it at 1440 and below
  it at 500; the term page's field reads `Diese Vorschriften
  durchsuchen` whole; OSDB-0004's panel starts at `Summenformel`; its
  eight `Anmerkung n` links resolve and `#note-3` tints the third note;
  the footer reads `Stand <date> <time>` on every page; in the dark
  scheme the home page and OSDB-0003 read as in the light one

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md` and the four authoring guides
- [x] 4.2 Archive
