## Why

`orgsyndb new` takes the next free procedure ID it sees in its own
clone, so two authors working in two clones can take the same ID, and
nothing records who took one. The owner settled in draft 07 that the
lab application issues procedure and sequence IDs, that the IDs a
collection already has are adopted, and that an ID the application did
not issue is refused; and, on 2026-11-12, that command-line tools sign
in with personal access tokens.

## What Changes

- Each account manages personal access tokens at
  `/lab/accounts/tokens/`: shown once, stored as a digest, revoked by
  deleting them; a token of an inactive account does not work.
- `POST /lab/collection/ids/`, signed with a token, issues the next
  procedure or sequence ID under the lock and records who took it,
  once the application has accepted an import.
- The first accepted import adopts every ID of its manifest and the
  IDs deleted in the collection's history, which the manifest now
  lists; every later import refuses an ID that was not issued.
  `manage.py adopt_ids` adopts IDs by hand, after a restore.
  Imported procedures and sequences are keyed by issued IDs.
- **BREAKING** `orgsyndb new` asks the application for the ID when the
  collection's own `registry` setting is an address, with the token
  from `ORGSYNDB_TOKEN` or `~/.config/orgsyndb/token`; with a registry
  file it takes the next free ID as before. `orgsyndb new --sequence`
  makes a sequence stub the same way.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: access tokens; the ID path in Permissions.
- `collection-import`: issued IDs, their adoption, the check of an
  import's IDs, the rows keyed by them, `deleted` in the manifest,
  and the lock.
- `build-script`: `new` takes its ID from the application, and makes
  sequence stubs; the manifest lists deleted IDs.
- `lab-demo`: the demo's import adopts its IDs; `--replace` deletes
  issued IDs and tokens.
- `container-deployment`: the builder's manifest carries `deleted`.

## Impact

- New: `accounts.AccessToken` with its page and admin;
  `collection.IssuedId` with its view; migrations.
- Changed: `webapp/collection/` (import, `adopt_ids`), `webapp/demo/`
  (`manifest.json` gains `deleted`), `tools/pipeline.py`,
  `tools/orgsyndb`, `deploy/docker/orgsyndb-deploy` (forwards
  `deleted`), `templates/sequence.md` (its ID placeholders), the
  docstring of Emacs's `orgsyndb-new-procedure`, the tests of each;
  `webapp/docs/database-schema.html`, regenerated.
- Docs: `README.md` (tokens, `orgsyndb new`, `adopt_ids` in the
  restore steps), `docs/AUTHORING*.md` and `docs/AUTHORING-ORG*.org`
  where they describe creating a procedure or a sequence.
