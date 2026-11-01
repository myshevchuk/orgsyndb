## Why

The reaction types a procedure may name live in the application, in
`site/data/reaction_types.toml`. Every collection built with one copy
of the application shares that list, and a group that classifies its
reactions differently has to edit the application. The list is the
collection's own data, like its compounds and the vocabularies its
declared fields name, and belongs beside them.

## What Changes

- **BREAKING** The reaction types are the collection's vocabulary
  `reaction-types`, the file `vocabularies/reaction-types.toml` beside
  its `orgsyndb.toml`, in the format of the other vocabularies. No value
  takes `parent`: the reaction types stay one level. A procedure still
  names exactly one of them. A collection without the file has no
  reaction type, so each of its procedures fails validation with
  `unknown reaction type "<v>"; see vocabularies/reaction-types.toml
  for the allowed values`.
- **BREAKING** `site/data/reaction_types.toml` and the whole `site/data/`
  directory go. The validator drops `--vocabulary`. It reads the
  reaction types from `vocabularies/` beside the settings file, as it
  reads every other vocabulary. A broken file is a configuration error
  with the vocabulary messages; a missing one is not.
- The application ships the former list as the starter vocabulary
  `templates/reaction-types.toml`. `init` copies it into a new
  collection, keeping a file already there, and the demo collection
  holds the same file.
- The build stages `build/data/reaction_types.json`, each value with its
  label in the site's language, and the site takes every reaction-type
  label from it. The Hugo overlay loses the `<site>/data` mount and has
  seven mounts.
- The Markdown templates point to `vocabularies/reaction-types.toml` for
  the allowed values.

## Capabilities

### New Capabilities

- `reaction-types`: the collection's reaction-type vocabulary, the
  starter vocabulary in `templates/`, and the reaction-type data the
  build stages for the site.

### Modified Capabilities

- `procedure-schema`: a procedure's reaction type is one of the
  collection's; the requirement on `site/data/reaction_types.toml` is
  removed; the Markdown template validates against the starter
  vocabulary and names the collection's file.
- `procedure-validation`: no `--vocabulary`; the reaction types follow
  the settings file; the default paths are the working directory's; the
  vocabulary errors, the fixture run and the fixtures change with them.
- `procedure-fields`: the procedure-field run reads the fixture reaction
  types from its copy.
- `compound-fields`: the reaction-type vocabulary is read though no
  declaration names it.
- `collection`: `vocabularies/` holds the reaction types; `init` writes
  them.
- `localization`: German reaction-type labels come from the collection's
  vocabulary.
- `site-build`: seven mounts; no `site/data/`; the reaction types reach
  Hugo as `site.Data.collection.reaction_types`.
- `build-script`: `build` stages `build/data/reaction_types.json`.
- `sample-procedures`: the demo holds `vocabularies/reaction-types.toml`.

## Impact

- Code: `tools/validate.py` (option, loading, messages),
  `tools/pipeline.py` (reaction-type data, overlay), `tools/orgsyndb`
  (`init`, staging), `site/layouts/_partials/reaction-type-label.html`.
- Files: `site/data/reaction_types.toml` moves to
  `templates/reaction-types.toml`; `examples/demo/vocabularies/` and
  `tests/fixtures/collection/vocabularies/` gain `reaction-types.toml`;
  `tests/fixtures/reaction_types.toml` and `bad-vocabulary.toml` give
  way to `tests/fixtures/settings/`.
- Docs: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`,
  `docs/AUTHORING.md`, `docs/AUTHORING.de.md`, `docs/AUTHORING-ORG.org`,
  `docs/AUTHORING-ORG.de.org`.
- Existing collections need a `vocabularies/reaction-types.toml`; the
  product has no users, so no migration is offered.
