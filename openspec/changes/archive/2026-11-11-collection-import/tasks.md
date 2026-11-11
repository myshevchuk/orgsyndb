## 1. Tests

- [x] 1.1 `manifest` subcommand and `pipeline.manifest_data`: the demo
  after a build, titles, the export required, Markdown only, arguments
- [x] 1.2 Imported rows: the models' constraints, protected
  references, the read-only admin
- [x] 1.3 Manifest view: token off, wrong token, malformed bodies, the
  method
- [x] 1.4 Accepting: first import, repeat, stale base, stale registry,
  a refused build
- [x] 1.5 Import checks: each error, nothing written on refusal
- [x] 1.6 Applying: matching by ID and signature, yields, new and
  withdrawn entries, a file gone and back, steps, the import of a row
- [x] 1.7 The lock: substance, term and article writes and the view take
  it; outside a transaction
- [x] 1.8 Imports page and the registry page's link; the snapshot's
  `import` and digest; `registry_load` round trip; the builder token
  setting; the manifest as the exception to sign-in; demo replacement
  after an import
- [x] 1.9 Builder: token, the accepted release at start, triggers,
  manifest contents and headers, accepted, refused, stale,
  unreachable, an answer lost after acceptance, failing manifest and
  index, a failed build reported and reported late, no build without
  a fresh snapshot; the fake application in `tests/`
- [x] 1.10 Caddyfile and `orgsyndb.env.example`

## 2. Implementation

- [x] 2.1 `pipeline.manifest_data` and `tools/orgsyndb manifest`
- [x] 2.2 `webapp/collection/`: models, migration, admin
- [x] 2.3 `orgsyndb_web.lock`; substance, term and article saves and
  deletions take it
- [x] 2.4 The manifest view: authentication, parsing, staleness,
  checks, applying, answers
- [x] 2.5 The snapshot's `import`; the imports page and its strings;
  the registry page's link
- [x] 2.6 `ORGSYNDB_BUILDER_TOKEN` in the settings; `registry_load`
  ignores `import`; `demo_data --replace` deletes the imported rows
- [x] 2.7 `orgsyndb-deploy`: staging, manifests, publishing after
  acceptance, the accepted release at start, the token and address,
  no build without a fresh snapshot, `registry.source` gone
- [x] 2.8 Caddyfile, `orgsyndb.env.example`
- [x] 2.9 `webapp/docs/database-schema.html` regenerated

## 3. Docs and archive

- [x] 3.1 `README.md`: builds and updates, the token, the imports page,
  `orgsyndb manifest`
- [x] 3.2 Review, then archive
