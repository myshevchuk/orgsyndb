# Change: Modularize lab.js with vendored Stimulus

## Why

`webapp/orgsyndb_web/static/lab.js` has grown into a ~1,260-line monolithic
IIFE whose features (`[popover]` placement, `data-remember`, `data-batch-for`,
`table[data-sortable]`, `#lab-dialog`, `.item-layout`, and `.planning-grid`)
duplicate master-detail selection/stepping logic and bind one-shot startup
listeners that do not automatically attach/detach across HTMX swaps. Vendoring
pinned Stimulus (`@hotwired/stimulus@3.2.2`, ~16 KB gzipped, MIT, zero build
chain, zero `eval`) and refactoring `lab.js` into focused Stimulus
controllers—while adopting native CSS Anchor Positioning for popovers with
`OrgSynLab.place` retained as fallback—gives clean lifecycle management and
unifies `.item-layout` and `.planning-grid` under one `split-list` controller.

## What Changes

- Vendor pinned `@hotwired/stimulus@3.2.2` (`dist/stimulus.umd.js` and its MIT
  `LICENSE.md` saved as `LICENSE`) under `webapp/orgsyndb_web/static/stimulus/`
  and load it with `defer` in `base.html` after `idiomorph-ext.min.js` and
  before `lab.js`.
- Update `openspec/specs/web-app/spec.md` (`Page shell` and `Scripts`) to
  include Stimulus in the shell script order and vendored-licence rules.
- Decompose `webapp/orgsyndb_web/static/lab.js` into Stimulus controllers
  registered with a custom schema (`actionAttribute: "data-lab-action"` so
  Stimulus never collides with `production-planning`'s `data-action="1"` on
  planning rows):
  1. `split-list` (`mode="htmx"` on `.item-layout` in `cotton/split_layout.html`,
     `mode="local"` on `.planning-grid` in `planning/list.html`) unifying row
     focusability, plain-click/Arrow-key stepping (`OrgSynLab.planStep`), and
     `aria-current`/`?selected=` helpers while strictly preserving each mode's
     selection timing (`local` immediate vs. `htmx` post-swap only).
  2. `sortable-table` on `table[data-sortable]` (`planning/list.html`,
     `inventory/item_page.html`).
  3. `dialog` on `#lab-dialog` (`base.html`).
  4. `popover-anchor` on `.lab-popup[popover]` (`inventory/item_list.html`)
     using native CSS Anchor Positioning (`@supports` + `@position-try` in
     `lab.css`) with `OrgSynLab.place` retained as runtime JS fallback, plus
     `view-menu` on `details.lab-view-menu`.
  5. `remember` on `[data-remember]` controls (`inventory/item_list.html`) and
     `batch-narrow` on `select[data-batch-for]` (`inventory/forms.py`).
- Preserve all six pure exports on `globalThis.OrgSynLab` (`place`,
  `paramSearch`, `narrowBatches`, `sortOrder`, `planFilterShows`, `planStep`),
  the no-eval `morph` extension override, the `beforeprint`/`afterprint`
  collapsible-widget fallback, and the live-list document guards.

## Impact

- Affected specs: `web-app` (`MODIFIED: Page shell`, `MODIFIED: Scripts`).
- Affected code: `webapp/orgsyndb_web/static/stimulus/{stimulus.umd.js,LICENSE}`,
  `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`,
  `webapp/orgsyndb_web/templates/cotton/split_layout.html`,
  `webapp/inventory/templates/inventory/{item_list,item_page}.html`,
  `webapp/planning/templates/planning/list.html`,
  `webapp/inventory/forms.py`,
  `webapp/orgsyndb_web/static/lab.css`,
  `webapp/orgsyndb_web/static/lab.js`.
- Affected tests: `webapp/tests/__init__.py` (`STIMULUS`, `shell_scripts`),
  `webapp/tests/test_shell.py` (`test_stimulus_kept_with_its_licence`),
  `webapp/tests/test_lab_script.py` (Stimulus schema, lifecycle/reconnect,
  `popover-anchor` native-vs-fallback, `split-list` `htmx`/`local` timing,
  `sortable-table`, `dialog` + in-place `#movements` morph refresh,
  `remember`, `batch-narrow` across both driver types, and template wiring).
