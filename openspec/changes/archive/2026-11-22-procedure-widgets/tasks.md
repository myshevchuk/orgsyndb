## 1. Tests

- [x] 1.1 Theme tests for "Procedure body sections": the eight
  sections of OSDB-0002 with their roles and kept ids, the German
  roles, the role table against `SECTIONS_BY_LANGUAGE`, the note
  links of OSDB-0003, the scope widget, and on every procedure page
  one `h2` per section and no `h2` of the body outside a section.
- [x] 1.2 Theme tests for "Metadata panel": widget titles and the new
  label order (OSDB-0002, every page's canonical order, OSDB-0907's
  `Products`), the context widget present exactly when it has a pair,
  one compound widget first, and the compound rows against the lab
  template's order.
- [x] 1.3 Theme tests for "Structure image slot" and "Procedure page
  structure": figures in the compound widget with
  `data-pagefind-ignore`, none in the header; scope between details
  and content.
- [x] 1.4 Update the tests that read the old order, the header
  figures or the removed `.procedure`/`.procedure-header`
  declarations (`tests/test_theme_integration.py`,
  `tests/test_theme_static.py`, `tests/test_localization_integration.py`,
  `tests/general_support.py`), the German panel scenario, and the
  tests that read the panel as one `dl.metadata`
  (`tests/sequence_support.py`, `tests/test_reaction_types.py`,
  `tests/test_catalogue_integration.py`, `tests/test_compound_links.py`),
  which read every list of `div.procedure-details` instead.

## 2. Templates

- [x] 2.1 `procedure-sections.html` partial with the role table;
  `procedures/page.html` uses it in place of `.Content`.
- [x] 2.2 `procedure-meta.html` becomes the three widgets;
  `structure.html` is called from the compound widget and marks its
  figures `data-pagefind-ignore`; `procedure-header.html` drops the
  figures.
- [x] 2.3 `scope-table.html` wraps the scope as a widget.
- [x] 2.4 Widget titles in `site/i18n/en.toml` and `de.toml`.

## 3. Styles

- [x] 3.1 `screen.css`: compact header, band of details widgets above
  the body widgets, `.widget dl.metadata` as a key–value table, body
  widgets at body font size with the reading measure and no clipping
  of the `:target` note highlight, notes beside Procedure and Workup
  on wide screens (design decision 3), single column below, a styled
  `.widget .structure__slot`; old procedure layout rules removed.
- [x] 3.2 `print.css`: `break-after: avoid` on `.widget__head`; the
  widgets print in document order without widget frames, each
  `.metadata` keeping its own frame; rules scoped to the procedure
  page, since lab pages load `print.css` too; the PDF tests of
  print-layout pass.

## 4. Verification

- [x] 4.1 Browser at 1440, 1000 and 500 px, light and dark: OSDB-0005,
  OSDB-0009 (general, scope) and OSDB-0002; no horizontal page scroll,
  notes beside the steps at 1440, single column at 500.
- [ ] 4.2 Owner checks a procedure page on the test server.
- [x] 4.3 PDF build: warning-free; page images of OSDB-0003, 0004 and
  0008 show nothing clipped and the structure on the first page.
