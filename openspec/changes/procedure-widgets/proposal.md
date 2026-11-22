## Why

A procedure page is the last page built from Markdown-style stacked
headings: a title block with the structure drawing, a flat 16-row
metadata list that mixes the compound's facts with the procedure's
record and its synthesis links, and eight body sections as plain `h2`
headings. The owner chose mockup A of the widget survey for it, with
the notes beside the procedure steps, so that the page reads like the
lab's substance and item pages: the same compound widget, small
key–value widgets and every body section in a widget of its own.

## What Changes

- The structure figures leave the procedure header and open a
  compound widget, `Verbindung` (`Compound`) for one product and
  `Produkte` (`Products`) for several, which holds the product rows of
  the metadata panel in the order of the lab's compound widget.
- The metadata panel becomes three widgets in the details wrapper:
  the compound widget; `Angaben` (`Details`) with the reaction type,
  tags, authors, checkers, declared fields and dates; and
  `Synthesekontext` (`Synthesis context`) with the starting materials,
  precursors, used-in procedures and sequences. Each holds a
  `dl.metadata`; the panel is their pairs in order. `Starting
  materials` moves from after the product facts to the context widget.
- Every `h2` section of the rendered body becomes a `section.widget`
  whose title bar holds the heading, keeping its `id`, and which
  carries the section's role (`summary`, `reagents`, `procedure`,
  `workup`, `characterization`, `notes`, `hazards`, `references`). A
  general procedure's scope becomes a widget too.
- On wide screens the details widgets form a band above the body
  widgets, and the `Notes` widget stands beside the `Procedure` and
  `Workup` widgets, which refer to it. Narrow windows and print keep
  the document order: header, details, scope, body.
- The layout positions that site-theme "Measure and tables" fixes for
  `.procedure` and `.procedure-header` are removed from the spec; the
  layout is the stylesheet's.

No data, no build step and no script are added. The PDF keeps its
single-column order and its warning-free WeasyPrint run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-theme`: "Measure and tables" loses the procedure layout
  declarations; "Procedure page structure", "Metadata panel" and
  "Structure image slot" describe the widgets; a new requirement
  "Procedure body sections" wraps the body's sections.
- `localization`: "Interface strings" names the German widget titles,
  and its metadata-panel scenario follows the new label order.

## Impact

- `site/layouts/procedures/page.html`, `site/layouts/_partials/`
  (`procedure-header.html`, `procedure-meta.html`,
  `structure.html`, `scope-table.html`, a new partial for the body
  sections), `site/i18n/{en,de}.toml`.
- `site/assets/css/screen.css` and, where the widgets need it in
  print, `site/assets/css/print.css`.
- Tests in `tests/test_theme_integration.py`,
  `tests/test_theme_static.py`, `tests/test_localization_integration.py`,
  `tests/general_support.py`, `tests/sequence_support.py`,
  `tests/test_reaction_types.py`, `tests/test_catalogue_integration.py`
  and `tests/test_compound_links.py` that read the panel as one list,
  its order, the header's figures or the removed declarations.
- The search index is unchanged: the widget titles and the moved
  figures are kept out of it.
