# Design: HTMX plumbing and Idiomorph DOM morphing

## Context

`webapp/inventory/views/common.py` is the single module in `webapp/` that
reads or writes raw `HX-*` headers (`htmx_detail_or_redirect`, `for_dialog`,
`sign_in_next`, `item_form`, and `saved`). All other inventory view modules
delegate HTMX branching to it.

On the client, `webapp/orgsyndb_web/static/lab.js` refreshes `[data-refresh][id]`
regions after a dialog save (`lab-saved`) by fetching the current page HTML,
parsing it with `DOMParser`, and calling `old.replaceWith(document.adoptNode(next))`.
Replacing whole subtrees destroys element-local state, requiring manual
`widgetOpen` and `boxScroll` maps in `refreshPage()`.

## Decisions

### 1. Use `django-htmx` while preserving exact HTTP contracts

- Add `django-htmx>=1.29` to `webapp/pyproject.toml` and enable
  `django_htmx` + `django_htmx.middleware.HtmxMiddleware` in
  `webapp/orgsyndb_web/settings.py` (placed after `CommonMiddleware`, before
  view execution).
- In `webapp/inventory/views/common.py`:
  - `htmx_detail_or_redirect`: check `if not request.htmx:` instead of
    `request.headers.get("HX-Request") != "true"`.
  - `for_dialog`: return `bool(request.htmx and not request.htmx.history_restore_request)`.
  - `sign_in_next`: read `current = request.htmx.current_url or ""`, validate
    with `url_has_allowed_host_and_scheme(current, {request.get_host()}, request.is_secure())`
    first, then parse with `urlsplit(current)` and return
    `(parts.path or "/") + (f"?{parts.query}" if parts.query else "")`
    (falling back to `request.path`). Using `request.htmx.current_url` rather
    than `request.htmx.current_url_abs_path` preserves exact compatibility for
    same-host HTTPS URLs on HTTP requests, scheme-relative URLs, local paths,
    and malformed host strings (which fail validation before `urlsplit()`).
  - `item_form`: return
    `HttpResponseClientRedirect(redirect_to_login(sign_in_next(request)).url, status=204)`.
    Passing `status=204` explicitly preserves the `204 No Content` contract
    (empty body + `HX-Redirect`) asserted by `test_inventory_dialogs.py` and
    `test_inventory_categories.py`, because `HttpResponseClientRedirect`
    defaults to `200`.
  - `saved`: return `trigger_client_event(HttpResponse(status=204), "lab-saved", {key: record.pk})`.
- Keep all `@vary_on_headers("HX-Request", ...)` decorators intact.

### 2. Vendor `idiomorph` `0.8.0` (`idiomorph-ext.min.js`) beside its `LICENSE`

- Store `dist/idiomorph-ext.min.js` (~11 KB, 0BSD) and `LICENSE` from
  `idiomorph@0.8.0` under `webapp/orgsyndb_web/static/idiomorph/`.
- `idiomorph-ext.min.js` bundles both the `Idiomorph` global (`Idiomorph.morph`)
  and the `htmx.defineExtension("morph", ...)` registration in one file.
- CSP verification: `idiomorph-ext.min.js` contains no `eval(...)`. Its HTMX
  extension invokes `Function(...)` for any unrecognized `morph:` suffix
  without consulting `htmx.config.allowEval`; the three standard styles
  (`morph`, `morph:outerHTML`, `morph:innerHTML`) never reach `Function(...)`.
  To enforce this under `web-app` `Scripts`, the spec and shell tests restrict
  every `hx-swap` / `data-hx-swap` attribute whose swap style begins with
  `morph` to those three exact styles (ignoring optional space-separated
  modifiers such as `scroll:top`).
- Load `idiomorph/idiomorph-ext.min.js` with `defer` in `base.html` after
  `htmx/htmx.min.js` and before `lab.js`, and add `hx-ext="morph"` to `<body>`.
  Existing `hx-swap="outerHTML"` and `hx-swap="innerHTML"` requests are
  unaffected because the `morph` extension ignores non-`morph` swap styles.

### 3. Morph `[data-refresh][id]` in place in `lab.js`

- In `refreshParts(fresh)`:
  - For each `[data-refresh][id]` element `old` where `fresh.getElementById(old.id)`
    exists, call `Idiomorph.morph(old, next, REFRESH_MORPH)` instead of
    `old.replaceWith(document.adoptNode(next))`, and push `old` onto `added`
    so callers still run `htmx.process(node)` and `enhanceSortable(node)` on
    each morphed subtree.
  - `REFRESH_MORPH` defines `callbacks.beforeAttributeUpdated`:
    ```js
    const REFRESH_MORPH = {
      callbacks: {
        beforeAttributeUpdated: (attr, node) => !(
          attr === "open" && node.matches("details.widget")
        ),
      },
    };
    ```
    Server-rendered `details.widget` elements carry no `open` attribute, so
    without this callback Idiomorph would remove `open` from a collapsible
    widget the user opened before saving. With it, `<details class="widget">`
    preserves both open and closed states natively across morphs.
- Remove `widgetOpen` save/restore loop from `refreshPage()`.
- Keep `boxScroll` save/restore loop in `refreshPage()`:
  - `.table-scroll` around `#movements` sits inside `#item-refresh` and has no
    ID of its own, and `#detail-vessels-scroll` sits inside `#item-detail`;
    moreover `sortTable()` re-appends rows after morphing. Retaining
    `boxScroll` after `sortTable()` guarantees both vertical and horizontal
    scroll offsets survive across all three scroll-box layouts without
    depending on unverified browser layout anchoring.
- Keep `ticked` (`input[name=item]`) restoration in `refreshPage()` /
  `restoreList(ticked)`:
  - Table rows in `item_list.html` carry `data-item` rather than `id`, so if a
    dialog save reorders rows (e.g. when sorted by stock), position-based
    morphing would otherwise keep a checkbox state on the wrong row. Preserving
    the `ticked` set by checkbox `value` remains exact regardless of row order.
- Keep `tableSort` capture and `sortTable()` re-application in `refreshPage()`:
  - Server HTML arrives in server order with plain `<th>` elements; morphing
    updates cell text and removes `.sort-header` buttons, after which
    `enhanceSortable(node)` and `sortTable()` restore the buttons, `aria-sort`,
    and sorted row order.

## Alternatives Considered

- **Vendor separate `idiomorph.min.js` + `idiomorph-htmx.js`**: Rejected
  because `idiomorph-ext.min.js` is an official single-file build (~11 KB)
  that exposes both `Idiomorph` and the `morph` HTMX extension with one fewer
  `<script>` tag in `base.html`.
- **Use `request.htmx.current_url_abs_path` in `sign_in_next`**: Rejected
  because it requires an exact scheme/netloc match (rejecting same-host HTTPS
  on HTTP, scheme-relative URLs, and local paths) and calls `urlsplit()`
  before validation. Using `request.htmx.current_url` with
  `url_has_allowed_host_and_scheme` preserves exact behavior.
- **Use `HttpResponseClientRedirect` default status `200`**: Rejected because
  existing tests and `item_form` docstring contract specify `204 No Content`
  with an empty body. Passing `status=204` keeps the contract intact with zero
  test churn.
- **Drop `ticked` checkbox restoration via `beforeAttributeUpdated`**:
  Rejected because `item_list.html` rows do not carry `id` attributes; if a
  save changes sort order, ignoring `checked` on position-matched rows would
  move ticks to different items.
- **Remove `boxScroll` save/restore loop**: Rejected because `#movements`
  scrolls inside `#item-refresh` and `sortTable()` reorders its rows after
  morphing; without browser-layout tests asserting scroll preservation,
  retaining the 16-line `boxScroll` restoration is safer.
