## Why

Since `lab-registry`, the lab application keeps substances and every
vocabulary, but the collection still has registries of its own:
`compounds/`, `vocabularies/` and the compound fields declared in
`orgsyndb.toml`, which the validator, the export, the site and Emacs
read. The two can disagree, and a substance added in the application
never reaches the site. The owner has settled that substances and
vocabularies are created and edited in the application only, and that
the collection names them by key, a file naming an unknown key being
refused. This change makes the collection read the application's
registry and removes its own.

## What Changes

- **BREAKING** A collection names its registry in `orgsyndb.toml`:
  `registry`, the address of the lab application's snapshot or the path
  of a snapshot file. `ORGSYNDB_REGISTRY` overrides it. The tools read
  the snapshot through one function, which caches a fetched snapshot in
  `build/registry.json` and falls back to that copy, with a warning,
  when the address cannot be reached.
- **BREAKING** `compounds/`, `vocabularies/` and `fields.compound` go
  from collections. Procedures name substances by their registry keys;
  reaction types, the vocabularies of procedure fields and every other
  term come from the registry.
- The site shows the registry's substances as it showed compounds, and
  four registry fields as it showed declared ones: the article number,
  the short name, the chemical classes and the group, with the
  presentation the demo collection declared for them. A structure image
  is the collection's `static/structures/<key>.svg` or `.png`.
- The validator takes `--registry FILE` in place of `--compounds`, and
  checks procedure and sequence keys, reaction types and procedure
  field values against the snapshot. Compound files are no longer
  checked: the application checks substances.
- `orgsyndb index` describes the registry's substances and vocabularies
  instead of files, with each substance's page in the lab application
  where the registry is an address.
- Emacs completes and checks against that index; going to a substance
  opens its page in the lab application, and the commands that created
  and visited compound files go.
- The container builder fetches the snapshot from `app` before every
  build, and builds again when its digest changes.
- The demo collection names `webapp/demo/registry.json` as its
  registry, so the GitHub Pages build needs no application; the test
  collections carry a snapshot file instead of compound and vocabulary
  files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `compound-registry`: the collection's registry is the lab
  application's snapshot; how a collection names it and how the tools
  read it.
- `compound-fields`: the registry fields the site shows replace
  declared compound fields.
- `procedure-fields`, `reaction-types`, `procedure-schema`:
  vocabularies and reaction types from the registry.
- `procedure-validation`, `build-script`, `collection`,
  `collection-index`: the validator's and the commands' inputs, the
  collection layout, `init`, and the index.
- `site-theme`, `site-catalogue`, `localization`: compound pages,
  directory, catalogue and tabs from the registry; German names and
  labels from it.
- `emacs-mode`: collection data, completion, definitions, the commands
  that go.
- `sample-procedures`, `demo-site`: the demo and test collections.
- `container-deployment`: the builder and the registry.
- `lab-registry`: the demo registry is the demo collection's registry;
  `registry_import` remains for collections in the old layout.

## Impact

- Changed: `tools/validate.py`, `tools/pipeline.py`, `tools/orgsyndb`,
  the Hugo layouts that read `data/compounds` where they assume a
  compound file's fields, the Emacs package, `deploy/docker/orgsyndb-deploy`,
  `examples/demo/`, `tests/fixtures/`, `templates/`, the repository's
  tests and the lab application's tests of `registry_import`.
- Removed: `examples/demo/compounds/`, `examples/demo/vocabularies/`,
  the fixture compound and vocabulary files, `templates/compound.toml`
  and `templates/reaction-types.toml`.
- Docs: `README.md` (compound registry, fields, Emacs, deployment), and
  the help pages `docs/AUTHORING.md`, `docs/SCHEMA.md` and their German
  versions and `docs/GLOSSARY.de.md`, where they describe compound files
  or vocabularies.
