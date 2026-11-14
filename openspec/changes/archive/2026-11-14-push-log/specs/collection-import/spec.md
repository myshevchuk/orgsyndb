## ADDED Requirements

### Requirement: Wake-up after a registry write
When `ORGSYNDB_WAKE_URL` is set (web-app "Settings from the environment"), the application SHALL wake the builder (container-deployment "Waking the builder") once after each committed transaction that saved or deleted a row the snapshot's digest covers, whatever fields it changed and through whichever path One lock lists (a model's save or deletion, a bulk update, creation or deletion, an account's save of fields the snapshot carries, `registry_load` and `registry_import`): by `POST` to that address with `Authorization: Bearer <ORGSYNDB_BUILDER_TOKEN>` and a timeout of 2 seconds, after the transaction commits. A failed or refused wake-up is logged as a warning and leaves the write as it is. A transaction that is rolled back, and one that writes only other rows, such as an import, an issued ID, a sign-in's last login or a task step, sends none; a write inside a savepoint that is rolled back counts for nothing, and a later write in the same transaction still wakes the builder once. Without the setting it sends none.

#### Scenario: A substance saved
- **WHEN** `ORGSYNDB_WAKE_URL` names a recording test server and a test saves a substance through its form, and in one transaction saves two terms
- **THEN** the server received one `POST` with the builder token after the first commit, and one after the second

#### Scenario: Every write path, once each
- **WHEN** a test saves a project through the admin, renames an account and changes another's display name, saves a notebook, updates two substances by one bulk update, and runs `registry_load` on an empty registry
- **THEN** the server received one `POST` per transaction, one for `registry_load` however many rows it wrote

#### Scenario: A savepoint rolled back
- **WHEN** in one transaction a test saves a substance inside a savepoint it rolls back, then saves another substance, and commits
- **THEN** the server received one `POST`

#### Scenario: Rolled back and other writes
- **WHEN** a test saves a substance in a transaction it rolls back, accepts an import, issues an ID, signs an account in and plans a task step
- **THEN** the server received nothing

#### Scenario: The builder does not answer
- **WHEN** `ORGSYNDB_WAKE_URL` names an address that refuses connections and a test saves a substance through its form
- **THEN** the save succeeds, the substance is stored, and a warning is logged

#### Scenario: No setting
- **WHEN** `ORGSYNDB_WAKE_URL` is empty and a test saves a substance
- **THEN** no request is sent

## MODIFIED Requirements

### Requirement: Imported rows
The lab application SHALL keep, in its package `collection`, these records:

- an import, one per build the builder reports: `build`, a UUID, unique; `commit`, the collection commit, 40 lowercase hexadecimal digits; `committed_at`; `base`, the accepted import it was built after, or none; `snapshot`, the registry digest it was built with, 64 lowercase hexadecimal digits; `tooling`, the application commit the builder ran, 40 lowercase hexadecimal digits; `release`, the release the builder staged for it, empty for a refused build; `language`, `de` or `en`, empty for a refused build; `outcome`, `accepted` or `refused`; `trigger`, `commit`, `registry`, `tooling` or `catch-up`; `pushed_by`, the account that pushed the commit (Manifest), or none; `errors`, one error per line, empty for an accepted import; and `received_at`;
- a procedure: `key`, its ID, an issued ID (Issued IDs), unique; `source`, `org` or `md`; `title`; `title_de`, which may be empty; `reaction_type`, a reaction type of the registry; `general`, whether it is a general procedure; `journal_entry`, the journal entry it was written from (lab-journal "Notebooks and entries"), or none, no two procedures that are not withdrawn naming one; `project`, a term of the registry's projects, or none; `last_import`, the accepted import that created it or last changed it; and `withdrawn`;
- a procedure author: its `procedure`; a `user`, an account; and `position`, its place among the procedure's authors, from 1, each account once per procedure;
- a scope entry: its `procedure`; `signature` (Applying an import), unique within the procedure; `position`, from 1; and `withdrawn`;
- an entry substance: its `entry`; a `substance` of the registry; `role`, `substrate` or `product`; `yield_percent`, for a product only, which may be none; and `position`, its place among the entry's substances of that role, from 1, each substance once per role;
- a sequence: `key`, its ID, an issued ID, unique; `title`; `title_de`, which may be empty; `target`, a substance; `last_import`; and `withdrawn`;
- a step: its `sequence`; `position`, from 1, unique within the sequence; and `entry`, a scope entry.
- an issued ID: `key`, an `OSDB-NNNN` or `SEQ-NNNN`, unique; `user`, the account it was issued to, or none for an adopted ID; and `issued_at`.

Only the manifest view (Accepting an import) writes them, the ID view and `adopt_ids` writing issued IDs (Issued IDs), and the demo data command, which records the data set's own import the same way (lab-demo "Demo data command"). Tasks name a sequence and their steps name scope entries and imports (task-tracker "Task record"). An import never deletes a procedure, scope entry or sequence; a substance, reaction type, project, scope entry, journal entry or account that a row names cannot be deleted, and only `demo_data --replace` deletes these records, with the other lab records (lab-demo "Demo data command"). The admin lists imports, procedures, sequences and issued IDs for staff, read-only, with no way to add, change or delete one.

#### Scenario: Read-only in the admin
- **WHEN** a staff user requests the admin's change page of an imported procedure and posts to its add and delete pages
- **THEN** the change page shows no editable field and no save button, and the add and delete pages answer 403

#### Scenario: A substance in use
- **WHEN** an accepted import names `acetic-anhydride` as a substrate and a test deletes that substance
- **THEN** the deletion raises a protected error and the substance stays

### Requirement: Manifest
`POST /lab/collection/manifest/` SHALL take a manifest, a JSON object with these keys:

- `format`: `1`;
- `build`: a UUID;
- `commit`: 40 lowercase hexadecimal digits;
- `committed_at`: an ISO 8601 date and time with an offset;
- `base`: the id of an import, or `null`;
- `snapshot`: 64 lowercase hexadecimal digits;
- `tooling`: 40 lowercase hexadecimal digits;
- `trigger`: `commit`, `registry`, `tooling` or `catch-up`;
- `pusher`: the user name of the account that pushed the commit, as Forgejo reports it, or `null`;
- `outcome`: `built` or `refused`;
- for `refused`, `errors`: a non-empty list of strings;
- for `built`, `release`: a non-empty string, and `language`, `procedures`, `sequences` and `deleted` as `tools/orgsyndb manifest` prints them (build-script "manifest subcommand").

The request SHALL carry `Authorization: Bearer <token>`, where `<token>` equals `ORGSYNDB_BUILDER_TOKEN`, compared in constant time. With that setting empty the path answers 404 to every request; with another token or none it answers 403. A method other than POST answers 405. A body that is not a JSON object of these keys and types answers 400 with `{"error": <reason>}`. None of these answers records anything. An import's `pushed_by` is the account whose user name equals `pusher`, ignoring case, or none when `pusher` is `null` or no account has that name; the pusher never refuses an import. The view is exempt from CSRF checks. Every answer is JSON.

#### Scenario: No token configured
- **WHEN** `ORGSYNDB_BUILDER_TOKEN` is empty and a test client posts a valid manifest with any token
- **THEN** the answer is 404 and no import exists

#### Scenario: Wrong token
- **WHEN** `ORGSYNDB_BUILDER_TOKEN` is `s3cret` and a test client posts a valid manifest with `Bearer other`, and once with no `Authorization` header
- **THEN** both answers are 403 and no import exists

#### Scenario: Malformed manifest
- **WHEN** a test client posts with the right token the bodies `not json`, `[]`, a manifest without `commit`, one whose `commit` has 39 digits, one whose `trigger` is `push`, one without `pusher` and one whose `pusher` is `7`
- **THEN** each answer is 400 with an `error`, and no import exists

#### Scenario: The pusher
- **WHEN** a test client posts with the right token a valid manifest whose `pusher` is `JKoch`, one whose `pusher` is `orgsyndb`, which no account has, and one whose `pusher` is `null`
- **THEN** each is recorded as an import, and their `pushed_by` are the account `jkoch`, none and none; the demo data command's import has none

#### Scenario: Not a POST
- **WHEN** a test client requests the path with GET and the right token
- **THEN** the answer is 405

### Requirement: Imports page
`/lab/collection/` SHALL need no sign-in and show the heading `Importe` (`Imports`) and, when an import was accepted, a line naming the latest accepted import's commit, its first ten digits, its release and its received time, and the number of procedures and of sequences not withdrawn. Below, a table lists the imports newest first with the columns `Empfangen` (`Received`), `Commit`, the first ten digits, `Anlass` (`Trigger`), as `Commit`, `Register` (`Registry`), `Werkzeuge` (`Tooling`) or `Nachholen` (`Catch-up`), `Gepusht von` (`Pushed by`), the display name of the import's `pushed_by`, empty for none, `Ergebnis` (`Outcome`), as `Angenommen` (`Accepted`) or `Abgelehnt` (`Refused`), `Release`, and `Fehler` (`Errors`), a refused import's errors, one per line. Without imports the table is replaced by `Noch keine Importe.` (`No imports yet.`).

#### Scenario: Imports listed
- **WHEN** the demo data set is written, the demo manifest was accepted and a failed build was reported, and a test client that is not signed in requests `/lab/collection/`
- **THEN** the page answers 200, the table lists the refused import first with its errors and then the accepted one, the refused one with the display name of the account its manifest named as `pusher`, and the line above names the accepted commit and the demo's numbers of procedures and sequences

#### Scenario: Nothing imported
- **WHEN** a test client requests `/lab/collection/` before any import
- **THEN** the page shows `Noch keine Importe.` and no table
