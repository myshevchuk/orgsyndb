## 1. Tests, red first

- [x] 1.1 Catalogue fixtures in `tests/fixtures/catalogue/`: valid Markdown
  procedures, untagged so both locales publish them, with mixed statuses
  (`checked`, `retired`), several authors and tags, an author `Ä. Müller`,
  a procedure without `product.cas`, two that share the newest `lastmod`
  instant, and titles that differ only in case and in a leading number;
  a harness helper copies them into a sandbox
- [x] 1.2 Node tests of `catalogue-core.js`: loading without a DOM,
  `parse` and `serialize`, `sortOf`, `withQuery`, `clear`, `select`
  matching, counts and orders, and the searcher against stubs
- [x] 1.3 Real-index tests: the `id` filter and sort key, the searcher
  against `meta.id` for every findability search, findability through
  the searcher, and the German index
- [x] 1.4 HTML scans: catalogue page, rows, controls and script wiring;
  term pages and their scope; Details markup; page shell, navigation and
  header search; stylesheets; home page; taxonomy pages; hidden buttons;
  German catalogue, home page and titles; the path-prefix resolution; the
  printed chrome texts
- [x] 1.5 Static checks: narrow-window columns, no `--pagefind-ui-`
  variables, `OrgSynSearch` with `normaliseTerm` only
- [x] 1.6 Remove the tests of the search page, both procedure lists, the
  list tools, `list-filter.js`, `cleanResult` and the four label filters

## 2. Catalogue on /procedures/

- [x] 2.1 `procedure-table.html` with five columns, row records and the
  Details block; catalogue partials for the head, `noscript` note,
  controls and script; `section.html`; the interface strings
- [x] 2.2 `catalogue-core.js`: `parse`, `serialize`, `active`, `sortOf`,
  `withQuery`, `clear`, `select`
- [x] 2.3 The `id` filter and sort key on the procedure header; the label
  filters removed; `search-terms.js` reduced to `normaliseTerm`; the
  searcher in `catalogue-core.js`
- [x] 2.4 `catalogue.js`: start, rendering, history, stale results,
  focus, counts, messages, index errors, narrow toggle and view switch;
  the concatenated, fingerprinted script
- [x] 2.5 Screen and print styles for the catalogue, its facets, chips,
  messages and the Details view

## 3. Term pages

- [x] 3.1 `term.html` on the shared catalogue: scope line, fixed facet,
  Browse all link; the script's fixed facet and link update

## 4. Shell, home and navigation

- [x] 4.1 Site header: three links, header search except on catalogue and
  term pages, `aria-current` rules
- [x] 4.2 Home page: lede, Recently updated, browse list with counts and
  shortcuts; screen styles
- [x] 4.3 Remove `/search/`, `/procedures-by-date/`, their content files
  and layouts, `list-tools`, `list-filter-script`, `sort-links`,
  `search.js`, `list-filter.js`, the Pagefind UI variables and the unused
  interface strings

## 5. Suite

- [x] 5.1 Relevant tests green, then the full suite, with and without
  Node: 389 passed and 1 skipped (`caddy`) with Node; 345 passed and 45
  skipped (`node`, `caddy`) without

## 6. Browser checks

Headless Firefox over WebDriver BiDi, against `tools/orgsyndb serve` or a
static server of a sandbox build; each item records what was checked.

- [x] 6.1 Searching and filtering together; SMILES substrings in the
  catalogue; no SMILES index text on the page. Checked: `cinnamate`
  rows equal Pagefind's `meta.id` order; status and tag selections narrow
  them; every shown facet count matches the rule recomputed from the
  rows; chips and `n of 14 procedures`; the five SMILES queries give the
  spec's sets; no index text in the page
- [x] 6.2 Direct address, reload, Back and Forward; one history entry per
  typing run; ignored parameters; a delayed search overtaken by a newer
  query. Checked: `?q=acid&type=hydrolysis&sort=title&view=details`
  restores controls and title order, also after reload; sort and facet
  changes push one entry each; clearing the field and typing `ester` with
  320 ms pauses adds one; Back three times and Forward once restore each
  snapshot; `?type=nope&tag=` shows the notice and becomes `/procedures/`;
  with `acid` delayed 2.5 s in a wrapped bundle, the later `aspirin`
  results stay
- [x] 6.3 Keyboard-only use, focus outlines and focus after chip removal
  and Clear all. Checked: Tab reaches the field, summaries, checkboxes,
  both selects and the table links, each with a visible outline; Space
  toggles a checkbox and a summary; Enter on a chip focuses the next chip,
  then the field; Clear all focuses the field; a toggled checkbox keeps
  focus
- [x] 6.4 Term page scope, Clear all and Browse all. Checked on
  `/tags/cinnamate/`: an author outside the scope (`c. example` in the
  fixture build, where A. Example has a cinnamate procedure) shows as a
  selection counting 0 with no rows; the fixed tag is checked, disabled
  and alone; with a sort, `acid` and `draft`, every row carries the tag;
  Browse all leads to `/procedures/?q=acid&status=draft&sort=title`, which
  opens with that state; Back and Clear all leave `?sort=title` and the
  scope
- [x] 6.5 Details view, narrow window at 500 CSS pixels, both colour
  schemes. Checked: Details keeps IDs and order and shows the fields, one
  lazy image (OSDB-0003), no broken image or empty link; filtered rows
  equal in both views; at 500 px the facets wait behind the toggle and
  `aria-expanded` follows; no horizontal page scroll on the catalogue,
  home, a term page and a procedure; screenshots in light and dark
  inspected
- [x] 6.6 Index error with `pagefind.js` removed. Checked: filters work
  without the index; a query gives no rows, `Search unavailable`, the
  error text and button and no counts; the button returns
  `/procedures/?status=draft` with its rows and focuses the field
- [x] 6.7 JavaScript disabled: catalogue, term page, header search, print
  and copy buttons. Checked: all 14 rows and the note, no control; the
  term page lists its rows with the scope line; the procedure page shows
  the header search and neither button; submitting the header search
  loads `/procedures/?q=aspirin` with the full list
- [x] 6.8 German build: catalogue texts, counts and messages. Checked:
  `8 Vorschriften`, `8 von 8 Vorschriften`, the chip `Status: Entwurf`
  and its label, the empty result, the ignored notice, the error, the
  loading text, and `Verseifung` finding OSDB-0001 and OSDB-0008
- [x] 6.9 The site under `/orgsyndb/`: links, assets and search.
  Checked: `?q=aspirin` lists OSDB-0002, its link opens a styled page,
  the header search works, and no request leaves `/orgsyndb/` apart from
  Firefox's own favicon probe and a font of its own as a `data:` URI
- [x] 6.10 Procedure pages: print button, copy button, sample banner,
  precursor links; a help page. Checked: both buttons shown, Copy reports
  its outcome, the banner, the precursor link to OSDB-0001, and `/help/`
  with the header search and three links marked; the print dialog itself
  was not opened headless

## 7. Docs and review

- [x] 7.1 Doc writer: `README.md` (introduction, "Use the site", search
  description)
- [x] 7.2 Codex reviewer on the branch: three findings in
  `catalogue.js` (a pending query lost to a click that does not blur the
  field, a chip replaced mid-click, row focus lost on new results), each
  reproduced in Firefox, fixed and rechecked with the section 6 pass
- [x] 7.3 Archive; bring the Purpose lines of the living `site-search` and
  `site-theme` specs in line with their requirements
