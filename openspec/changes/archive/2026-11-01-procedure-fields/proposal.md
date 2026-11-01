## Why

A group records facts about its procedures that the schema does not
know: the lab-notebook page a procedure was first run on, the project
or course it belongs to, its working time, whether it needs an inert
atmosphere. Today such a key draws an `unknown field` warning and the
site never shows it. Compounds already take fields that the collection
declares in its settings file; procedures should take them the same
way, with the same types and checks, shown in the metadata panel and
offered as filters of the procedure catalogue.

## What Changes

- `orgsyndb.toml` may declare `[[fields.procedure]]` beside
  `[[fields.compound]]`. A declaration takes the compound declaration's
  keys, apart from `column`, `search` and `tabs`. It shares the
  vocabularies under `vocabularies/`. Its keys must avoid the procedure
  schema's keys, Hugo's front-matter keys and the procedure catalogue's
  keys.
- The validator checks every procedure, Markdown source or Org export,
  against the declarations, with the compound fields' messages. A
  `unique` value is compared across procedures, not files. The language
  variants of a procedure share every declared value, as they share
  `status`. A declared key no longer draws `unknown field`.
- An Org source sets a declared field on a
  `#+HUGO_CUSTOM_FRONT_MATTER:` line. The export types the value as
  ox-hugo does, which rules out a text value made only of digits or
  reading `true` or `false`.
- `build/data/fields.json` gains `procedure` beside `compound`.
- The metadata panel shows each declared field a procedure sets, after
  `Checked by` and before `Created`. The value is written as on a
  compound page. Since the panel lies in the indexed text, the catalogue
  search finds the values.
- A `boolean` or `choice` field declared `facet = true` becomes a filter
  of every procedure catalogue (`/procedures/`, the term pages,
  `/general-procedures/`), between `Status` and `Tag`. Its rows carry
  the values, and a vocabulary value also selects the procedures filed
  under the values below it.
- The demo declares procedure fields of every type: `notebook`,
  `project` (a two-level vocabulary `projects`, a facet),
  `working_time` (hours) and `inert_atmosphere` (a facet). Every demo
  procedure, Org and Markdown, in both languages, sets them as the
  rules require, mirrored in the test collection.

## Capabilities

### New Capabilities

- `procedure-fields`: the `fields.procedure` declarations and their
  configuration errors, the checks of procedure values, the field data
  for procedures, the declared fields in the metadata panel and as
  filters of the procedure catalogues, and the Org route.

### Modified Capabilities

- `compound-fields`: `fields` may hold `procedure`; the field data
  holds `procedure` beside `compound`.
- `procedure-schema`: a declared procedure field is no key outside the
  schema.
- `procedure-validation`: `--settings` also governs the procedures.
- `localization`: variants share the declared procedure fields.
- `site-theme`: the declared fields in the metadata panel.
- `site-catalogue`: declared facets in the procedure catalogue's
  controls and rows.
- `sample-procedures`: the demo's procedure fields and the `projects`
  vocabulary.

## Impact

- `tools/validate.py`, `tools/pipeline.py`.
- Site: the metadata panel, the procedure catalogue and table partials,
  the field-value partial.
- `examples/demo/orgsyndb.toml`, `examples/demo/vocabularies/projects.toml`
  and every demo procedure, mirrored in the test collection.
- A new validator fixture `tests/fixtures/procedure-fields/`.
- Tests for the validator, the field data, the metadata panel, the
  procedure catalogue, localization, the Org export and the demo.
- Docs: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`, the two
  Markdown authoring guides and the two Org authoring guides.
