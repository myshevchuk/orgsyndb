## 1. Tests

- [x] 1.1 The hook `deploy/forge/push-log`: a line per update of main, none for other refs or a deletion, `-` for a missing pusher, the wake-up and its failure, an unwritable log, concurrent hooks
- [x] 1.2 The builder: `POST /wake` (tokens, 202, a cycle at once, coalesced), the server with only the builder token or none, `/check` without the gate token (replacing the test that no server runs without it), `pusher` from the push log (last line, none, missing file, a line appended during the build)
- [x] 1.3 The app: `pusher` in the manifest (required, a name or null), `pushed_by` set by user name or none, the demo data's import without one, the imports page's column, the admin
- [x] 1.4 The app's wake-up: each write path (form, admin, bulk queryset, account rename and display name, notebook, `registry_load`) wakes once after commit, a savepoint rolled back before a write, a rolled-back transaction, an import, an issued ID and a task step, a failing builder, no setting
- [x] 1.5 Deployment: compose's volume `pushes`, `forge-db` and `forge-setup` read checks (ownership, hook link, mirror), the example settings

## 2. Implementation

- [x] 2.1 `pushed_by`, its migration, `pusher` in the manifest, the imports page and the admin
- [x] 2.2 The app's wake-up and `ORGSYNDB_WAKE_URL`
- [x] 2.3 The builder: push log, `pusher`, `/wake`, the server's start
- [x] 2.4 `deploy/forge/push-log`, `forge-db`, `forge-setup`, compose, Dockerfile, example settings
- [x] 2.5 Local end-to-end run against Forgejo 15.0.11: the volume's ownership fresh and existing, HTTPS and SSH pushes logged with their pusher and waking the builder, the image's shell appending whole lines, the mirror synced

## 3. Docs and archive

- [x] 3.1 README: the push log and its volume, the settings, the mirror and its warning, who pushed
- [x] 3.2 Review, then archive
- [ ] 3.3 Test server, by the owner: rebuild, `ORGSYNDB_WAKE_URL`, `forge-setup` again; a push is built within seconds and the imports page names the pusher; a substance edit is rebuilt within seconds
