## Why

Since `collection-gate` the collection lives in `lab/collection` in
Forgejo and every push to `main` passes the gate, but the builder still
finds a push only by polling every `ORGSYNDB_INTERVAL` seconds, a
registry change waits for the same poll, an import does not say who
pushed the commit it was built from, and the collection's outside
remote no longer receives anything. Draft 07 closes these: a push log
that Forgejo writes and the builder reads, a wake-up after a push and
after a registry change, the pusher on every import, and a push mirror
to the outside remote.

## What Changes

- A post-receive hook `deploy/forge/push-log`, which `forge-setup`
  links into `lab/collection`, appends a line for each accepted update
  of `main` (time, commit, Forgejo's id and name of the pusher) to a
  push log on a new volume `pushes` that `forge` writes and `builder`
  reads, then wakes the builder.
- The builder's server (port 8091) also answers `POST /wake`, with the
  gate token or the builder token, and runs a cycle at once; it runs
  whenever either token is set. The poll stays as the backstop.
- The manifest gains `pusher`: the user name the push log names for
  the built commit, or `null`. The import keeps it as `pushed_by`, an
  account, and the imports page shows it.
- The app wakes the builder after a transaction that wrote a row the
  snapshot's digest covers commits, when `ORGSYNDB_WAKE_URL` is set.
- `forge-setup` adds a push mirror of `lab/collection` to
  `ORGSYNDB_MIRROR_URL` when it is set, with `ORGSYNDB_MIRROR_USER` and
  `ORGSYNDB_MIRROR_TOKEN`, synced on every push.
- New settings: `ORGSYNDB_PUSH_LOG`, `ORGSYNDB_WAKE_URL`,
  `ORGSYNDB_MIRROR_URL`, `ORGSYNDB_MIRROR_USER`, `ORGSYNDB_MIRROR_TOKEN`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-deployment`: the push log, the hook and its volume; the
  builder's server answering wake-ups; `pusher` in the manifest;
  `forge-setup` linking the hook and adding the mirror; the example
  settings.
- `collection-import`: `pushed_by` on imports, `pusher` in the
  manifest, the imports page's column, and waking the builder after a
  registry write.
- `web-app`: the setting `ORGSYNDB_WAKE_URL`.
- `database-diagram`: the link of `collection_import.pushed_by_id` to
  the accounts.

## Impact

- Changed: `deploy/docker/orgsyndb-deploy` (push log, `/wake`,
  `pusher`), `deploy/docker/Dockerfile` (the push log's mount point),
  `deploy/compose.yaml` (volume `pushes`), `deploy/forge/forge-db`,
  `deploy/forge/forge-setup`, new `deploy/forge/push-log`,
  `deploy/orgsyndb.env.example`; `webapp/collection/` (model,
  migration, manifest, page, admin), `webapp/orgsyndb_web/` (wake-up,
  setting); German messages; the tests of each.
- Docs: README (services and volumes, settings, Forgejo set-up, the
  mirror and its warning, who pushed on the imports page).
- Test server: rebuild, `ORGSYNDB_WAKE_URL` in `orgsyndb.env`,
  `forge-setup` again. No mirror there: its collection is the
  application's own repository, which a push mirror would overwrite.
