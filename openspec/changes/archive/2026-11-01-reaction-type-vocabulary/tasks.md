## 1. Tests and fixtures, red first

- [x] 1.1 Fixtures: `tests/fixtures/settings/` (`orgsyndb.toml`,
  `vocabularies/reaction-types.toml`) in place of
  `tests/fixtures/reaction_types.toml` and `bad-vocabulary.toml`; the
  fixture run passes `--settings`; the settings variant run; the
  field-declaration and procedure-field runs copy the fixture reaction
  types; `tests/fixtures/collection/vocabularies/reaction-types.toml`;
  every existing test that passes `--vocabulary` or reads
  `site/data/reaction_types.toml`, and every one that validates a
  procedure without a settings file or `vocabularies/` in its working
  directory (stubs `new` writes, the baseline from an empty working
  directory), moved to the new contract
- [x] 1.2 Validator: the working directory's reaction types, a
  collection without them, nested values, an unknown entry key, the
  configuration errors (no label, not TOML, empty `label_de`), a
  missing file that is no configuration error, `--vocabulary` refused,
  the default-path scenarios, the unknown-reaction-type message, a
  declared field naming `reaction-types` with and without the file
- [x] 1.3 Starter vocabulary and templates: the template well formed and
  accepted; the Markdown templates name
  `vocabularies/reaction-types.toml` and validate against the starter
  vocabulary
- [x] 1.4 Pipeline: `reaction_types_data` in both languages, without a
  German label, without a file, with a nested value; the overlay's
  seven mounts; no `site/data/`
- [x] 1.5 Build and site: `build/data/reaction_types.json` staged; the
  site's labels follow the collection's vocabulary
- [x] 1.6 Collection: `init` writes the starter vocabulary and keeps an
  existing one; the demo matches `init`; the demo's vocabularies

## 2. Implementation

- [x] 2.1 `tools/validate.py`: no `--vocabulary`; the reaction types
  from `vocabularies/reaction-types.toml` beside the settings file,
  with the vocabulary rules and no `parent`; a missing file gives none;
  the new message
- [x] 2.2 `tools/pipeline.py`: `reaction_types_data`; the overlay
  without `<site>/data`
- [x] 2.3 `tools/orgsyndb`: `build` stages `build/data/reaction_types.json`;
  `init` copies the starter vocabulary
- [x] 2.4 Site: `reaction-type-label.html` reads
  `site.Data.collection.reaction_types`; `site/data/` removed
- [x] 2.5 `templates/reaction-types.toml`; the comments of
  `templates/procedure.md` and `templates/procedure.de.md`
- [x] 2.6 Demo: `examples/demo/vocabularies/reaction-types.toml`

## 3. Verification

- [x] 3.1 Full suite: 1033 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: a German demo build shows the reaction-type labels on
  `/reaction_types/`, a term page, the catalogue facet, a procedure
  table row, a metadata panel and a sequence page. Driven through
  Marionette in headless Firefox: the list read Acylierung (1) to
  Veresterung (1) in alphabetical order; the term page of
  `aldol-condensation` had the `h1` and title Aldolkondensation; the
  facet listed the same seven labels in the same order; the row of
  OSDB-0003 and the panel of OSDB-0002 showed Veresterung and
  Acylierung; the two sequence pages read Hydrolyse, Acylierung and
  Kreuzkupplung, Reduktion

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`,
  the two Markdown and the two Org authoring guides (`docs/AUTHORING.md`
  already correct); the Org guides' schema links made plain file links
- [x] 4.2 Codex reviewer: the test of a new collection's first stub
  passed when validation aborted; it now requires exit status 0
- [x] 4.3 Archive
