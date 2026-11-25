## Context

`site/assets/js/catalogue.js` reads the fixed facet once from
`div.catalogue[data-fixed]` and binds the header search form through
`document.getElementById("catalogue-q").form`. CSS targets neither
`[data-catalogue-search]` nor `details[data-fixed]`.

## Goals / Non-Goals

- **Goals:** Remove both unused DOM attributes from the Hugo partials,
  the `site-catalogue` spec, and the HTML test assertions.
- **Non-Goals:** Changing `div.catalogue[data-fixed]`, `#catalogue-q`,
  the fixed facet's `checked`/`disabled` checkbox, or any JS behavior.

## Decisions

- Keep `data-fixed` on `div.catalogue`, which `catalogue.js` reads.
- Replace the `data-catalogue-search` check in `test_theme_integration.py`
  with checking `id="catalogue-q"` on the search input iff the page is a
  catalogue page.
