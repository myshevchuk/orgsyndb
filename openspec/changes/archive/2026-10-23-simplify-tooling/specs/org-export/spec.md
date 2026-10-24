## MODIFIED Requirements

### Requirement: Export plan
`pipeline.write_export_plan(org_root, plan_path)` SHALL plan exactly the entries that `validate.discover(org_root, ".org")` returns with no problem attached, the files the validator examines as Org procedures. Every other entry, such as a dotfile like the Emacs lock symlink `.#OSDB-0001-x.org`, a subdirectory or a file not ending in `.org`, is left out of the plan and so produces no export. It lints each planned file with the validator's Org keyword lint and then acts as follows:
- If any file has a lint error, it prints the validator-format problem lines to stderr, deletes any earlier plan file, and returns None.
- Otherwise it writes `plan_path`, creating its directory, and returns the plan. The file is a JSON array sorted by file name. Each element has `source` (absolute path), `stem` (file name without `.org`), `date` and `lastmod` (RFC 3339 strings), and `ai_model` (the `#+AI_MODEL` value, or `null` when it is `none`).

A missing `org_root` yields an empty array.

#### Scenario: Plan for a valid source
- **WHEN** a test calls `write_export_plan` on a temporary Org root holding a copy of `tests/fixtures/valid/org/OSDB-0003-*.org`
- **THEN** it returns a plan, and the written plan has one element whose `stem` is that file's stem, whose `date` is `2026-10-19T17:42:05+02:00`, and whose `ai_model` is `null`

#### Scenario: Entries the validator does not examine are not planned
- **WHEN** a test calls `write_export_plan` on a temporary Org root holding a copy of `tests/fixtures/valid/org/OSDB-0003-*.org`, a dangling symlink named `.#OSDB-0003-x.org`, a regular file `.OSDB-0005-hidden.org`, a subdirectory `nested.org/`, and `notes.txt`
- **THEN** it returns a plan, and the written plan has exactly one element, the `OSDB-0003` source

#### Scenario: Lint error stops the plan
- **WHEN** a test calls `write_export_plan` on `tests/fixtures/org-invalid/missing-seconds/org`
- **THEN** it returns None, stderr contains a line with field `#+CREATED` containing `must have the form [YYYY-MM-DD Day hh:mm:ss]`, and no plan file exists

### Requirement: Complete and fresh export directory
`tools/orgsyndb export` SHALL leave `build/export/` holding exactly one `<stem>.md` for each planned Org source of `org/procedures/`, and no other file. It uses the sibling directories `build/.export-staging/` and `build/.export-previous/` in these steps:
1. **Recover.** `pipeline.recover_export(build)` runs first:
   - If `.export-previous/` exists and `export/` does not, it renames `.export-previous/` to `export/`.
   - If both exist, it deletes `.export-previous/`.
   - It deletes any `.export-staging/`, and empties `build/tmp/`.
2. **Stage.** The export writes into a new, empty `.export-staging/`.
3. **Install.** `pipeline.check_staging(build, plan)` and then `pipeline.replace_export(build, rename, remove)` run. `rename` defaults to `os.rename` and `remove` to `shutil.rmtree`; both are injectable so that tests can make a step fail:
   1. It checks that the staging directory holds exactly the planned files.
   2. It renames an existing `export/` to `.export-previous/`.
   3. It renames `.export-staging/` to `export/`. When that rename fails, it renames `.export-previous/` back to `export/` before failing.
   4. It deletes `.export-previous/`. A failure of this delete is a warning only.

When there are no Org sources, `build/export/` exists and is empty. When any step fails, the command exits 1, and `build/export/` holds its previous contents, either directly or after the next run's recovery step.

#### Scenario: Deleted source leaves no orphan
- **WHEN** an integration test exports, deletes one Org source, and exports again
- **THEN** that source's `.md` is absent from `build/export/`, and every other export is still present

#### Scenario: Failed export keeps the previous directory
- **WHEN** an integration test exports successfully, then changes one source's `#+CREATED` to `[2026-10-19 Mon 17:42]` and exports again
- **THEN** the second export exits 1, and `build/export/` holds the same files with the same bytes as after the first export

#### Scenario: Second rename fails
- **WHEN** a unit test builds `build/export/` (one file `A.md`) and `build/.export-staging/` (one file `B.md`), and calls `replace_export` with a `rename` that fails on its second call
- **THEN** `replace_export` raises, `build/export/` holds exactly `A.md` with its original bytes, and `build/.export-previous/` does not exist

#### Scenario: Restore fails too
- **WHEN** the same test uses a `rename` that fails on its second and third calls
- **THEN** `replace_export` raises with a message saying that the next export will recover
- **AND** a following call of `recover_export` leaves `build/export/` holding exactly `A.md`, with no `.export-previous/` and no `.export-staging/`

#### Scenario: Backup deletion fails after a successful swap
- **WHEN** the same test lets both renames succeed but passes a `remove` that raises `OSError`
- **THEN** `replace_export` returns normally, `build/export/` holds exactly `B.md`, and a following call of `recover_export` removes `.export-previous/`

#### Scenario: Leftovers from a crashed run
- **WHEN** an integration test leaves `build/.export-previous/` holding a complete earlier export with no `build/export/`, plus a partial `build/.export-staging/`, and then runs `tools/orgsyndb -C <collection> export`
- **THEN** the export exits 0, `build/export/` holds exactly the current exports, and neither `.export-previous/` nor `.export-staging/` remains

#### Scenario: No Org sources
- **WHEN** an integration test removes every file from `org/procedures/` and exports
- **THEN** the export exits 0, and `build/export/` exists and is empty

