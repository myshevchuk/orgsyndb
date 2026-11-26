# Change: HTMX plumbing and Idiomorph DOM morphing

## Why

The lab application currently inspects raw `HX-Request`,
`HX-History-Restore-Request`, and `HX-Current-URL` headers and builds raw
`HX-Redirect` and `HX-Trigger` JSON headers by hand in
`webapp/inventory/views/common.py`. Meanwhile, `refreshParts()` and
`refreshPage()` in `webapp/orgsyndb_web/static/lab.js` replace every
`[data-refresh][id]` region with `old.replaceWith(node)`, which forces manual
save/restore bookkeeping for collapsible `<details class="widget">` open state
and `.table-scroll` scroll offsets.

Adopting `django-htmx` on the server and vendoring `idiomorph` on the client
replaces the manual HTMX header plumbing with standard middleware/response
helpers, morphs refreshed regions in place so DOM-owned state survives
natively, and prepares the page shell (`hx-ext="morph"`) for HTMX-driven live
list updates in later changes.

## What Changes

- **Specs (`web-app`)**:
  - Update `Page shell` so pages load `/lab/static/htmx/htmx.min.js`,
    `/lab/static/idiomorph/idiomorph-ext.min.js`, and then
    `/lab/static/lab.js`, all with `defer`.
  - Update `Scripts` so `idiomorph` is a vendored library kept at a fixed
    version beside its `LICENSE` under `webapp/orgsyndb_web/static/idiomorph/`,
    and restrict `morph` values on `hx-swap` / `data-hx-swap` attributes to
    the three non-evaluating styles (`morph`, `morph:outerHTML`,
    `morph:innerHTML`).
- **Backend (`webapp/`)**:
  - Add `django-htmx` to `webapp/pyproject.toml` and `webapp/uv.lock`.
  - Register `"django_htmx"` in `INSTALLED_APPS` and
    `"django_htmx.middleware.HtmxMiddleware"` in `MIDDLEWARE` in
    `webapp/orgsyndb_web/settings.py`.
  - Refactor `htmx_detail_or_redirect`, `for_dialog`, `sign_in_next`,
    `item_form`, and `saved` in `webapp/inventory/views/common.py` to use
    `request.htmx`, `HttpResponseClientRedirect(..., status=204)`, and
    `trigger_client_event(...)`, preserving all existing HTTP status codes,
    redirect semantics, response headers, and `@vary_on_headers` decorators.
- **Frontend (`webapp/orgsyndb_web/`)**:
  - Vendor `idiomorph` `0.8.0` (`dist/idiomorph-ext.min.js` and `LICENSE`,
    0BSD) under `webapp/orgsyndb_web/static/idiomorph/`.
  - Load `idiomorph/idiomorph-ext.min.js` with `defer` between `htmx.min.js`
    and `lab.js` in `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`,
    and add `hx-ext="morph"` to `<body>`.
  - Update `refreshParts()` and `refreshPage()` in
    `webapp/orgsyndb_web/static/lab.js` to morph `[data-refresh][id]` elements
    in place via `Idiomorph.morph(old, next, ...)` with a
    `beforeAttributeUpdated` callback that preserves `open` on
    `details.widget`, removing the manual `widgetOpen` save/restore loop while
    retaining `boxScroll`, `ticked` checkbox restoration, and client-side
    `tableSort` re-application.

## Impact

- Affected spec: `openspec/specs/web-app/spec.md` (`Page shell`, `Scripts`).
- Affected code: `webapp/pyproject.toml`, `webapp/uv.lock`,
  `webapp/orgsyndb_web/settings.py`,
  `webapp/orgsyndb_web/static/idiomorph/idiomorph-ext.min.js`,
  `webapp/orgsyndb_web/static/idiomorph/LICENSE`,
  `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`,
  `webapp/orgsyndb_web/static/lab.js`, `webapp/inventory/views/common.py`.
- Affected tests: `webapp/tests/__init__.py`, `webapp/tests/test_shell.py`,
  `webapp/tests/test_inventory_dialogs.py`, `webapp/tests/test_lab_script.py`.
- No database migrations, no URL changes, and no user-facing documentation
  changes.
