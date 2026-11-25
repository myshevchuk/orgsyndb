## Why

`site-catalogue` requires `data-catalogue-search` on `form.site-search`
and `data-fixed` on the fixed `details.facet`. Neither `catalogue.js`
nor any stylesheet reads either attribute: `catalogue.js` finds the
search form through `#catalogue-q` (`field.form`) and reads the fixed
facet from `div.catalogue[data-fixed]`. Both attributes exist solely to
satisfy tests.

## What Changes

- Remove `data-catalogue-search` from `site/layouts/_partials/site-header.html`
  and from `site-catalogue` ("Catalogue controls").
- Remove `data-fixed` from `details.facet` in
  `site/layouts/_partials/catalogue.html` and from `site-catalogue`
  ("Fixed scope on term pages"), keeping `data-fixed` on
  `div.catalogue`.
- Update catalogue and theme integration tests accordingly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-catalogue`: drop `data-catalogue-search` on `form.site-search`
  and `data-fixed` on `details.facet`.

## Impact

- `openspec/specs/site-catalogue/spec.md`
- `site/layouts/_partials/site-header.html`,
  `site/layouts/_partials/catalogue.html`
- `tests/catalogue_support.py`, `tests/test_catalogue_integration.py`,
  `tests/test_theme_integration.py`
