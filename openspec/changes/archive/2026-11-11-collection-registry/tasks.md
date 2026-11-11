## 1. Fixtures

- [x] 1.1 `tests/fixtures/registry.json`, the fixture registry, made from
  the former `tests/fixtures/compounds/` and fixture reaction types, with
  the projects of the procedure-field fixture; remove
  `tests/fixtures/compounds/`, `tests/fixtures/fields/` and the
  `vocabularies/` of `tests/fixtures/settings/` and
  `tests/fixtures/procedure-fields/`
- [x] 1.2 `tests/fixtures/collection/registry.json`, a copy of
  `webapp/demo/registry.json`; its `orgsyndb.toml` names it; remove its
  `compounds/` and `vocabularies/`
- [x] 1.3 `webapp/tests/fixtures/old-layout/`: the demo collection's
  former `orgsyndb.toml`, `compounds/` and `vocabularies/`, for the
  tests of `registry_import`

## 2. Tests

- [x] 2.1 Registry source and reader: path, environment, address with
  cache and fallback, `store=False`, not a snapshot, none named
- [x] 2.2 Validator: `--registry`, its default, refused options, registry
  errors, unknown compounds and reaction types, a substance named
  `group`, the fixture runs and variant runs on the fixture registry
- [x] 2.3 Procedure fields: declarations, errors (`fields.compound`
  among them), values and messages, Org export values, field data;
  vocabularies from the registry
- [x] 2.4 Field data and display: the four registry fields, labels,
  values, order, beside values
- [x] 2.5 Reaction types from the registry: validator, site data, labels
- [x] 2.6 Collection layout and `init`; `validate` and `index`
  subcommands; index data
- [x] 2.7 Site: staged substance data and the overlay mount; compound
  catalogue, tabs, directory and pages; German names; images by key;
  substances without formula, molar mass or SMILES
- [x] 2.8 Sample collections: the demo and test collections as specified
- [x] 2.9 Emacs: index, completion in sequences, substance definitions,
  new procedure, preview, problem locations, file kinds
- [x] 2.10 Builder: registry fetch with its `Host`, the digest in the
  combination, the copy when unreachable
- [x] 2.11 Lab application: `registry_import` on the old-layout fixture

## 3. Implementation

- [x] 3.1 `pipeline.registry` and the snapshot check
- [x] 3.2 Validator on the snapshot: `--registry`, keys, reaction types,
  procedure vocabularies, removal of compound and vocabulary file checks
- [x] 3.3 `fields_data` and `reaction_types_data` from the registry; the
  four registry fields
- [x] 3.4 Build: staged `build/data/compounds/`, the overlay mount,
  structure images by key; site layouts where they assumed a
  compound's formula, molar mass or SMILES
- [x] 3.5 `index_data`, `orgsyndb validate`, `index` and `init`
- [x] 3.6 Emacs package
- [x] 3.7 `orgsyndb-deploy`
- [x] 3.8 `examples/demo/` and the test fixtures; remove the compound and
  reaction-type templates
- [x] 3.9 Lab application tests: the old-layout fixture

## 4. Docs and archive

- [x] 4.1 `README.md`: the registry a collection names, the fields the
  site shows, the validator's options, Emacs, the builder
- [x] 4.2 Help pages `docs/AUTHORING*.md`, `docs/SCHEMA*.md` and
  `docs/GLOSSARY.de.md` where they describe compound files or
  vocabularies
- [x] 4.3 Review, then archive
