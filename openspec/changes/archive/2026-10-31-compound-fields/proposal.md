## Why

A compound carries a fixed set of fields: names, formula, weight,
SMILES, CAS number and structure image. A research group keeps more
about its compounds than that, and what it keeps differs from group to
group: an internal item number, a short name, its own classification
of compounds, a stock level. None of it belongs in the application,
which would have to guess every group's fields. Today such a key is
only an `unknown field` warning, and the site never shows it.

## What Changes

- A collection declares the extra fields of its compounds in its
  `orgsyndb.toml`, as `[[fields.compound]]` tables: a key, a type
  (`text`, `number`, `boolean` or `choice`), English and German labels,
  whether the field is required, and whether the compound directory
  shows it as a column. A text field may have a pattern and be unique;
  a number field may have bounds, a unit, and be unique; a choice field
  names a vocabulary and may take several values.
- A collection's vocabularies are files `vocabularies/<name>.toml`,
  shaped like the reaction-type vocabulary, whose values may be filed
  under a parent value, so that a classification can have levels.
- The validator gains `--settings`, the collection's `orgsyndb.toml`.
  It checks the declarations and vocabularies, where a fault is a
  configuration error, and checks each compound's values against them.
  A declared key no longer draws `unknown field`.
- `orgsyndb.toml` accepts `fields` beside `format`. The program's own
  check of the file stays shallow, so `clean` and `new` still work
  while a declaration is broken.
- The build stages the declarations, with their labels in the site's
  language and the vocabularies resolved, as `build/data/fields.json`,
  which an eighth Hugo mount exposes as `site.Data.collection.fields`.
- A compound page shows the declared fields its compound sets after
  the built-in facts; the compound directory adds a column for each
  field declared with `column = true`.
- The demo collection declares fields of every type, with a
  three-level classification, and its compounds set them; the test
  collection copies them. The compound template points to the
  collection's own fields.

## Capabilities

### New Capabilities

- `compound-fields`: field declarations, vocabularies, their
  configuration errors, the checks of compound values, the field data
  the build stages for the site, and how the site writes a value.

### Modified Capabilities

- `compound-registry`: declared keys are not unknown; the compound
  template mentions the collection's own fields.
- `collection`: `vocabularies/` in the layout; `fields` in
  `orgsyndb.toml`; the demo's `orgsyndb.toml` no longer equals the one
  `init` writes.
- `procedure-validation`: the `--settings` option and its default; the
  field-declaration run and the `fields/` fixtures.
- `build-script`: `validate` passes `--settings`; `build` stages the
  field data.
- `site-build`: the eighth mount.
- `site-theme`: declared fields on compound pages and as directory
  columns.
- `sample-procedures`: the demo's declarations, vocabulary and values,
  copied into the test collection.

## Impact

- `tools/validate.py`, `tools/pipeline.py`, `tools/orgsyndb`.
- Site: the compound page and directory layouts, a partial for the
  declared fields, the strings `Yes` and `No` in both i18n files.
- Content: `examples/demo/orgsyndb.toml`, `examples/demo/vocabularies/`
  and every demo compound, mirrored in `tests/fixtures/collection/`;
  `templates/compound.toml`; new fixtures under `tests/fixtures/fields/`.
- Tests for the validator, the pipeline, the build, the samples, the
  templates and the compound pages.
- Docs: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`, and the
  authoring guides where they describe adding a compound.
