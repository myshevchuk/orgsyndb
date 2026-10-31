## 1. Tests and fixtures, red first

- [x] 1.1 Fixtures `tests/fixtures/fields/`: `orgsyndb.toml` and
  `vocabularies/chemical-classes.toml` and `vocabularies/storage.toml`
  as procedure-validation "Fixture suite" states
- [x] 1.2 Validator: the field-declaration run helper; declarations,
  vocabularies and their configuration errors; field values,
  `required` and `unique`; `--settings` and its default; a declared
  key draws no `unknown field`
- [x] 1.3 Pipeline: `fields_data` in both languages and without a
  settings file; the overlay's eight mounts
- [x] 1.4 Program: the marker accepts `fields`, `clean` ignores a broken
  declaration, `validate` passes `--settings`, `build` stages
  `build/data/fields.json`; the demo's `orgsyndb.toml` against `init`'s
- [x] 1.5 Samples: the demo's declarations, vocabulary and values; the
  test collection copies `vocabularies/`
- [x] 1.6 Template: the closing comment of `templates/compound.toml`
- [x] 1.7 Site: declared fields on every compound page and as directory
  columns, in English and German; markup in a label and a value

## 2. Implementation

- [x] 2.1 `tools/validate.py`: the settings loader, vocabularies,
  value checks, `--settings`
- [x] 2.2 `tools/pipeline.py` and `tools/orgsyndb`: `fields_data`, the
  eighth mount, the marker check, the validator arguments, the staged
  field data
- [x] 2.3 Demo collection: `orgsyndb.toml`, `vocabularies/`, the values
  in every compound; the same files in the test collection
- [x] 2.4 `templates/compound.toml`
- [x] 2.5 Site: the declared-fields partial, the compound page and
  directory, `Yes` and `No` in both i18n files

## 3. Verification

- [x] 3.1 Full suite: 792 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: a compound page with every type of field and the
  directory's columns, on the German demo build, light and dark, at
  1280 and 500 CSS pixels. Checked in headless Firefox: the page of
  ethyl (triphenylphosphoranylidene)acetate shows Artikelnr.,
  Stoffklasse with both paths, Bestand `12,5 g` and Eigene Herstellung
  `Nein`; the directory shows Artikelnr. and Stoffklasse. The two new
  columns, kept on one line, squeezed the name column until compound
  names broke mid-word; the columns of declared fields now wrap

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA.md`,
  `docs/SCHEMA.de.md`, and the authoring guides where they describe
  adding a compound; both Org guides' pass lines corrected from
  `gpt-6` to `gpt-6.1-sol`
- [x] 4.2 Codex reviewer: one finding, a pattern too large to compile
  crashed the validator; fixed with a regression test
- [x] 4.3 Archive
