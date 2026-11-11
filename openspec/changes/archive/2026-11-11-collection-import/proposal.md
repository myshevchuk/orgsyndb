## Why

The lab application knows the collection's procedures and sequences
only through `index.json`, a file the builder drops into each release:
it matches tasks against IDs in that text, holds nothing of a
procedure's scope entries, and cannot tell which commit a running
synthesis followed. The owner has settled that the application holds
the part of the collection it needs as its own rows, written only by
the import of an accepted collection commit, so that what is planned
and made keeps its link to the procedure even after the file changes.
This change adds that import: the builder sends the application a
manifest of every build, the application checks it against its
registry and records it, and the site publishes only what the
application accepted.

## What Changes

- A new `collection` package in the lab application holds imports,
  procedures, their scope entries and the substances of each entry,
  and sequences with their steps. Only an accepted import writes them.
  A row whose file or line is gone is marked withdrawn, never deleted.
- A scope entry is identified by its chemistry: the signature
  `substrates >> products` of sorted substance keys, unique within its
  procedure. Yields, positions and conditions change freely; changing
  the substances makes a new entry and withdraws the old one.
- `tools/orgsyndb manifest` prints the collection part of a manifest
  after a build: the site language, the procedures with their entries
  and the sequences with their steps.
- The builder sends every build, accepted or failed, to the
  application at `POST /lab/collection/manifest/`, signed with a
  service token, `ORGSYNDB_BUILDER_TOKEN`. Caddy does not forward that
  path. A failed build is recorded as refused with its errors.
- The application accepts a manifest under one lock that every
  registry write also takes, only while the import it was built after
  is still the latest accepted one and its registry digest is still
  current; otherwise it answers stale and the builder builds again. A
  repeated build is answered as before.
- **BREAKING** The builder stages a release before sending the
  manifest and switches the site to it only once the application has
  accepted it. It builds whenever the collection commit, the registry
  digest or its own application commit differs from the latest
  accepted import's, which the snapshot names, and at start points the
  site at that import's release.
- The snapshot gains `import`, the latest accepted import, outside its
  digest, so that accepting an import starts no build.
- `/lab/collection/` lists the imports with their outcome, trigger,
  commit, release and the errors of a refused one.

## Capabilities

### New Capabilities

- `collection-import`: the imported rows, the manifest the application
  accepts, how an import is checked and applied, the lock, and the
  imports page.

### Modified Capabilities

- `lab-registry`: the snapshot names the latest accepted import.
- `build-script`: the `manifest` subcommand.
- `container-deployment`: the builder's token, its build decision,
  staged releases published after acceptance, no build without a fresh
  snapshot, and Caddy refusing the manifest path.
- `web-app`: the `ORGSYNDB_BUILDER_TOKEN` setting; the manifest as the
  one write without a signed-in user.
- `lab-demo`: replacing the demo data deletes the imported rows.

## Impact

- New: `webapp/collection/` (models, migration, manifest view,
  imports page, templates, German strings), `webapp/orgsyndb_web/lock.py`.
- Changed: `webapp/registry/`, `webapp/vocabulary/` and
  `inventory.Article` (saves and deletions take the lock; the
  snapshot's `import`), `webapp/demo/` (replacement), `webapp/orgsyndb_web/settings.py` and `urls.py`,
  `tools/orgsyndb` and `tools/pipeline.py` (manifest),
  `deploy/docker/orgsyndb-deploy`, `deploy/docker/Caddyfile`,
  `deploy/orgsyndb.env.example`, and the tests of each.
- Unchanged here: `index.json` and `orgsyndb_web.index`, which tasks
  still read until they move onto the imported rows in a later change;
  the collection's file formats.
- Docs: `README.md` (container deployment, builds and updates, the
  imports page, `orgsyndb manifest`) and
  `webapp/docs/database-schema.html`, regenerated.
