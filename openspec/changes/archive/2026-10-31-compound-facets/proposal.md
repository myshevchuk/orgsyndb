## Why

A collection can now declare its own compound fields, and the compound
directory shows some of them as columns, but a group with a hundred
compounds still has to scroll to find its ketones, the compounds it
makes itself, or the one whose item number it has in hand. The
procedure catalogue already filters and searches; its core, though,
knows only the five procedure facets, so the compound directory cannot
reuse it.

## What Changes

- The catalogue core takes its facets from the page instead of a fixed
  list: a state holds one key per facet the page names, `parse` learns
  the facets from `known` and the sorts and views from what the page
  offers, and with no sort chosen `select` keeps the page's order. The
  procedure catalogues behave as before.
- A declaration may say `facet = true` on a `boolean` or `choice` field
  and `search = true` on a `text` field. `id`, `title`, `created`,
  `modified`, `text`, `q`, `sort` and `view` become reserved field keys.
- `/compounds/` becomes the compound catalogue: a count, one filter per
  facet field, chips, `Clear all`, and the header search, which on that
  page searches compounds. A choice facet lists its vocabulary as a
  tree, and ticking a value also selects the compounds filed under the
  values below it. The search matches substrings of each compound's
  names, formula, CAS number, SMILES and searchable text fields, in the
  browser, without Pagefind. Without JavaScript the page is still the
  complete table.
- The field data gains `facet`, `search`, each value's `ancestors` and
  each vocabulary's depth-first `order`.
- The demo makes `chemical_class` and `in_house` facets and
  `item_number` and `short_name` searchable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `compound-fields`: the `facet` and `search` options, the reserved
  keys, and the field data's new keys.
- `site-catalogue`: the core's facets, offers and record order, the
  text search `match`, the compound catalogue, the script on
  `/compounds/`, and the browser behaviour of both kinds of catalogue.
- `site-theme`: the header search on `/compounds/`; the compound
  directory as the compound catalogue's table.
- `localization`: the compound catalogue's German strings.
- `sample-procedures`: the demo's facet and search fields.

## Impact

- `tools/validate.py` (options, reserved keys), `tools/pipeline.py`
  (field data).
- `site/assets/js/catalogue-core.js`, `site/assets/js/catalogue.js`,
  `site/assets/css/`; the compound directory layout, the header
  partial, the catalogue script partial, both i18n files.
- `examples/demo/orgsyndb.toml`, mirrored in the test collection.
- Tests for the validator, the field data, the catalogue core under
  Node, the compound directory, the page shell and localization.
- Docs: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`.
