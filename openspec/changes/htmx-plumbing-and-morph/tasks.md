# Tasks: HTMX plumbing and Idiomorph DOM morphing

## 1. Tests (red-first)
- [x] 1.1 Update `SHELL_SCRIPT` / `shell_scripts()` in `webapp/tests/__init__.py` to assert `/lab/static/idiomorph/idiomorph-ext.min.js` is loaded once with `defer`, after `htmx.min.js` and before `lab.js`.
- [x] 1.2 Add `test_idiomorph_kept_with_its_licence`, `hx-ext="morph"`, and morph swap-style CSP checks (rejecting any `morph:` value other than `morph`, `morph:outerHTML`, `morph:innerHTML`) in `webapp/tests/test_shell.py`.
- [x] 1.3 Add tests covering `django-htmx` middleware integration (`request.htmx`) and `sign_in_next` edge cases (same-host HTTPS on HTTP, scheme-relative URL, local path, host-only URL, fragment stripping, malformed host) in `webapp/tests/test_inventory_dialogs.py`.

## 2. Backend (`django-htmx`)
- [x] 2.1 Add `django-htmx>=1.29` to `webapp/pyproject.toml` and update `webapp/uv.lock`.
- [x] 2.2 Register `"django_htmx"` in `INSTALLED_APPS` and `"django_htmx.middleware.HtmxMiddleware"` in `MIDDLEWARE` in `webapp/orgsyndb_web/settings.py`.
- [x] 2.3 Refactor `htmx_detail_or_redirect`, `for_dialog`, `sign_in_next`, `item_form`, and `saved` in `webapp/inventory/views/common.py` to use `request.htmx`, `HttpResponseClientRedirect(..., status=204)`, and `trigger_client_event(...)`, keeping `@vary_on_headers` intact.

## 3. Frontend (`idiomorph` + `lab.js`)
- [x] 3.1 Vendor `idiomorph` `0.8.0` `dist/idiomorph-ext.min.js` and `LICENSE` under `webapp/orgsyndb_web/static/idiomorph/`.
- [x] 3.2 Update `webapp/orgsyndb_web/templates/orgsyndb_web/base.html` to load `idiomorph/idiomorph-ext.min.js` with `defer` between `htmx.min.js` and `lab.js`, and set `hx-ext="morph"` on `<body>`.
- [x] 3.3 Update `refreshParts()` and `refreshPage()` in `webapp/orgsyndb_web/static/lab.js` to morph `[data-refresh][id]` elements in place via `Idiomorph.morph` with `beforeAttributeUpdated` preserving `open` on `details.widget`, removing the manual `widgetOpen` save/restore loop while preserving `boxScroll`, `ticked` restoration, and `tableSort` re-application.

## 4. Verification
- [x] 4.1 Run `python3 -m pytest tests/test_webapp_layout.py` at the repository root and the webapp area suites (`test_shell.py`, `test_lab_script.py`, `test_inventory_dialogs.py`, `test_inventory_categories.py`, `test_inventory_lists.py`, `test_inventory_detail.py`, `test_inventory_bulk.py`, `test_inventory_notes.py`, `test_widgets_item_page.py`, `test_overview.py`) serially until green.
