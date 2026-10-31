## Why

A group sorts its compounds by an internal scheme before anything
else: what it buys and what it makes, or a storage area, or a project.
The compound directory can now filter by such a field, but the first
division a group thinks in deserves its own pages, one per group, that
work without JavaScript and can be linked, as the procedure section's
tabs divide procedures.

## What Changes

- A `choice` field may declare `tabs = true`, at most one field per
  collection. Its key then names a directory of tab pages, so the
  validator refuses a compound with the same key.
- `/compounds/` and one page per top-level value of that field's
  vocabulary, at `/compounds/<field key>/<value>/`, open with tabs:
  `All compounds`, then the values that some compound carries, in
  vocabulary order.
- A tab page is the compound catalogue for the compounds filed under
  its value: its own count, facets and search, its header search
  scoped to it. Where the tabs field is also a facet, the tab's own
  value leaves its facet and the levels below it remain as filters.
- The field data marks the tabs field.
- The demo gains a `group` field, its internal classification:
  purchased (starting materials, reagents) and synthesised
  (intermediates, final products), which drives the tabs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `compound-fields`: the `tabs` option, its configuration errors, the
  field data's `tabs`, and the rule against a compound named like the
  tabs field.
- `site-catalogue`: the compound tabs and tab pages, the catalogue
  script on them.
- `site-theme`: the header search and the navigation on tab pages;
  `nav.section-tabs` allowed on the compound catalogue's pages.
- `localization`: the German strings of the tabs.
- `sample-procedures`: the demo's `group` field and its vocabulary.

## Impact

- `tools/validate.py`, `tools/pipeline.py`.
- Site: the compound content adapter (tab pages), a layout for them, a
  partial for the compound tabs, the header partial, both i18n files.
- `examples/demo/orgsyndb.toml`, `examples/demo/vocabularies/` and
  every demo compound, mirrored in the test collection.
- Tests for the validator, the field data, the compound catalogue and
  tab pages, the page shell, localization and the demo.
- Docs: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`.
