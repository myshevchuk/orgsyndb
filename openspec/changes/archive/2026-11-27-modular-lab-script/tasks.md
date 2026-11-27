# Tasks: Modularize lab.js with vendored Stimulus

## 1. Tests (red-first)
- [x] 1.1 Update `webapp/tests/__init__.py` (`STIMULUS = "/lab/static/stimulus/stimulus.umd.js"`, `shell_scripts()` requiring `HTMX`, `IDIOMORPH`, `STIMULUS`, `LAB_SCRIPT` in order, all with `defer`) and add `test_stimulus_kept_with_its_licence` to `webapp/tests/test_shell.py`.
- [x] 1.2 Add unit and markup tests in `webapp/tests/test_lab_script.py` and `webapp/tests/test_shell.py` (or a new `webapp/tests/test_stimulus_controllers.py`) verifying:
  - Vendored `stimulus.umd.js` contains no `eval(` or `Function(` calls and loads in Node `vm` with `codeGeneration: { strings: false }`.
  - Custom `actionAttribute: "data-lab-action"`: with vendored `stimulus.umd.js` loaded, a `data-lab-action` descriptor fires once, an identical descriptor under `data-action` does NOT bind/fire, and `split-list` (`local` mode) still reads `data-action="1"` on planning rows.
  - `lab.css` includes `@supports (anchor-name: --a) and (position-anchor: --a) and (top: anchor(bottom)) and (position-try-fallbacks: flip-block)`, `@position-try --popover-fit` with 16 px viewport insets, and anchor bindings for `#stock-menu`, `#more-filters`, and `#columns-menu`.
  - `popover-anchor` skips `dataset.placed`/inline coordinates when all four `CSS.supports(...)` checks pass, falls back to `OrgSynLab.place` + `dataset.placed` when any check fails (including partial support), and closes `details.lab-view-menu[open]` in both cases.
  - `split-list` (`htmx` mode): clicking a row triggers `item-select` and sets `#item-detail.inert = true` without changing `aria-current`, URL `?selected=`, `#filter-selected`, or `OWN_LINKS` while pending; a failed/aborted request resets `inert` and leaves mark/URL/hidden input unchanged; a successful `htmx:afterSwap` updates all four; disconnecting and reconnecting handles an outside toolbar/radio click exactly once.
  - `split-list` (`local` mode): clicking or Arrow-stepping updates `aria-current`, `[data-article]` inspector blocks, focus, and `?selected=` immediately, and filter buttons read `data-action="1"`, `data-priority`, and `data-late="1"`.
  - `dialog` + `sortable-table` lifecycle: `a[data-dialog]` click from sibling `<main>` opens `#lab-dialog` via `htmx.ajax`, `posting`/`saving` guards `inert` and `cancel`, `lab-saved` runs `refreshPage()` morphing `#movements` (`table[data-sortable]`) in place, re-enhancing headers once, preserving active `aria-sort` order, closing the dialog, and returning focus; disconnecting and reconnecting `dialog` and `sortable-table` handles clicks exactly once (no duplicate listeners).
  - `remember` restores and saves checkbox/select values; `batch-narrow` narrows on initial connect and on driver updates for BOTH driver types (text substance input and `select` item dropdown with `option[data-substance]`), and changing one delivery-note row leaves another row's selected batch intact.
  - Template wiring check verifying `data-controller` attributes (`split-list`, `sortable-table`, `dialog`, `popover-anchor`, `view-menu`, `remember`, `batch-narrow`) render on their respective pages and pass `assert_scripts`.

## 2. Vendored Asset & Shell
- [x] 2.1 Vendor pinned `@hotwired/stimulus@3.2.2` (`dist/stimulus.umd.js` and MIT `LICENSE.md` saved as `LICENSE`) under `webapp/orgsyndb_web/static/stimulus/`.
- [x] 2.2 Update `webapp/orgsyndb_web/templates/orgsyndb_web/base.html` to load `stimulus/stimulus.umd.js` with `defer` between `idiomorph-ext.min.js` and `lab.js`, and add `data-controller="dialog"` to `#lab-dialog`.

## 3. Templates, Forms & CSS
- [x] 3.1 Add `data-controller` attributes to `webapp/orgsyndb_web/templates/cotton/split_layout.html` (`split-list` with `mode="htmx"`), `webapp/planning/templates/planning/list.html` (`split-list` with `mode="local"`, `sortable-table`), `webapp/inventory/templates/inventory/item_page.html` (`sortable-table`), `webapp/inventory/templates/inventory/item_list.html` (`popover-anchor`, `view-menu`, `remember`), and `webapp/inventory/forms.py` (`batch-narrow` on `BatchField`).
- [x] 3.2 Add `@supports (anchor-name: --a) and (position-anchor: --a) and (top: anchor(bottom)) and (position-try-fallbacks: flip-block)` and `@position-try --popover-fit` CSS Anchor Positioning rules for `#stock-menu`, `#more-filters`, and `#columns-menu` in `webapp/orgsyndb_web/static/lab.css`.

## 4. Script Refactor
- [x] 4.1 Refactor `webapp/orgsyndb_web/static/lab.js` into modular Stimulus controllers (`SplitListController`, `SortableTableController`, `DialogController`, `PopoverAnchorController`, `ViewMenuController`, `RememberController`, `BatchNarrowController`) registered with `actionAttribute: "data-lab-action"`, preserving all `globalThis.OrgSynLab` pure exports, the no-eval `morph` override, `beforeprint`/`afterprint`, and live-list document guards.

## 5. Verification
- [x] 5.1 Run the shell, script, overview, planning, inventory, stock-forms, widget, and live-list area suites serially (`test_lab_script.py`, `test_stimulus_controllers.py`, `test_shell.py`, `test_overview.py`, `test_planning_list.py`, `test_planning_inspector.py`, `test_inventory_dialogs.py`, `test_inventory_categories.py`, `test_inventory_lists.py`, `test_inventory_table.py`, `test_inventory_detail.py`, `test_inventory_stock_forms.py`, `test_inventory_live_lists.py`, `test_live_tasks_registry.py`, `test_widgets_item_page.py`, `test_widgets_substance_page.py`, `test_widgets_history.py`) until green.
