## Why

Since `collection-gate` and `push-log` the collection's home is
`lab/collection` in Forgejo, Forgejo keeps its accounts and settings in
its own database `forge`, and the push log names who pushed each
commit. The `backup` service still dumps only the lab database, so a
lost server loses the collection's repository, Forgejo and the push
log. Draft 07: the backup dumps the lab database first, then takes
Forgejo's data; since `main` only grows, every commit the lab dump
names is in the later copy.

## What Changes

- `backup` writes a backup set per run, a directory
  `orgsyndb-<UTC time>/` holding, all taken while Forgejo is paused,
  the lab database's dump, the push log, the `forge` database's dump
  and an archive of Forgejo's whole volume, and a copy of
  `orgsyndb.env`; written under a temporary name and renamed when
  complete, one run at a time. `ORGSYNDB_KEEP_BACKUPS` counts sets. **BREAKING**: the layout
  replaces `lab-<time>.dump`; earlier dumps are no longer pruned.
- Forgejo pauses on request: `forge-start` runs Forgejo as a child and
  stops it while the backup's request file exists on a new volume
  `forge-control`, so the backup copies Forgejo's data at rest; it
  first waits for pushes in flight, and the gate refuses new ones
  while a pause is asked for.
- `orgsyndb-backup restore <set>`, run through a new Compose service
  `restore` in the profile `restore`, recreates and restores both
  databases, Forgejo's volume and the push log from a set, removes the
  builder's clone of the collection, and prints the steps that keep
  `web` closed until IDs issued after the set are reconciled.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-deployment`: the backup requirement (renamed from
  "Database backups" to "Backups") covers sets, Forgejo's pause and
  restore; the Compose file's `backup` and `restore` services and the
  volume `forge-control`; `forge-start` pausing Forgejo; `forge-db`
  handing `forge-control` to UID 1000.

## Impact

- Changed: `deploy/backup/orgsyndb-backup`, `deploy/forge/forge-start`,
  `deploy/forge/forge-db`, `deploy/compose.yaml`; the tests of each.
- Docs: README (back up and restore, replacing "Back up and restore lab
  records"; the service list; Forgejo's pause during a backup).
- Test server: rebuild; the next backup writes a set and pauses Forgejo
  for its duration; old `lab-*.dump` files stay until removed by hand.
