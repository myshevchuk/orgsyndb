# collection-import Specification

## Purpose
Define how the lab application holds the collection's procedures, scope entries and sequences: the rows only an accepted import writes, the manifest the builder sends, how an import is accepted, checked and applied under one lock, and the page that lists the imports.
## Requirements
### Requirement: Imported rows
The lab application SHALL keep, in its package `collection`, these records:

- an import, one per build the builder reports: `build`, a UUID, unique; `commit`, the collection commit, 40 lowercase hexadecimal digits; `committed_at`; `base`, the accepted import it was built after, or none; `snapshot`, the registry digest it was built with, 64 lowercase hexadecimal digits; `tooling`, the application commit the builder ran, 40 lowercase hexadecimal digits; `release`, the release the builder staged for it, empty for a refused build; `language`, `de` or `en`, empty for a refused build; `outcome`, `accepted` or `refused`; `trigger`, `commit`, `registry`, `tooling` or `catch-up`; `errors`, one error per line, empty for an accepted import; and `received_at`;
- a procedure: `key`, its ID, unique; `source`, `org` or `md`; `title`; `title_de`, which may be empty; `reaction_type`, a reaction type of the registry; `general`, whether it is a general procedure; `last_import`, the accepted import that created it or last changed it; and `withdrawn`;
- a scope entry: its `procedure`; `signature` (Applying an import), unique within the procedure; `position`, from 1; and `withdrawn`;
- an entry substance: its `entry`; a `substance` of the registry; `role`, `substrate` or `product`; `yield_percent`, for a product only, which may be none; and `position`, its place among the entry's substances of that role, from 1, each substance once per role;
- a sequence: `key`, its ID, unique; `title`; `title_de`, which may be empty; `target`, a substance; `last_import`; and `withdrawn`;
- a step: its `sequence`; `position`, from 1, unique within the sequence; and `entry`, a scope entry.

Only the manifest view (Accepting an import) writes them, and the demo data command, which records the data set's own import the same way (lab-demo "Demo data command"). Tasks name a sequence and their steps name scope entries and imports (task-tracker "Task record"). An import never deletes a procedure, scope entry or sequence; a substance, reaction type or scope entry that a row names cannot be deleted, and only `demo_data --replace` deletes these records, with the other lab records (lab-demo "Demo data command"). The admin lists imports, procedures and sequences for staff, read-only, with no way to add, change or delete one.

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
- `outcome`: `built` or `refused`;
- for `refused`, `errors`: a non-empty list of strings;
- for `built`, `release`: a non-empty string, and `language`, `procedures` and `sequences` as `tools/orgsyndb manifest` prints them (build-script "manifest subcommand").

The request SHALL carry `Authorization: Bearer <token>`, where `<token>` equals `ORGSYNDB_BUILDER_TOKEN`, compared in constant time. With that setting empty the path answers 404 to every request; with another token or none it answers 403. A method other than POST answers 405. A body that is not a JSON object of these keys and types answers 400 with `{"error": <reason>}`. None of these answers records anything. The view is exempt from CSRF checks. Every answer is JSON.

#### Scenario: No token configured
- **WHEN** `ORGSYNDB_BUILDER_TOKEN` is empty and a test client posts a valid manifest with any token
- **THEN** the answer is 404 and no import exists

#### Scenario: Wrong token
- **WHEN** `ORGSYNDB_BUILDER_TOKEN` is `s3cret` and a test client posts a valid manifest with `Bearer other`, and once with no `Authorization` header
- **THEN** both answers are 403 and no import exists

#### Scenario: Malformed manifest
- **WHEN** a test client posts with the right token the bodies `not json`, `[]`, a manifest without `commit`, one whose `commit` has 39 digits and one whose `trigger` is `push`
- **THEN** each answer is 400 with an `error`, and no import exists

#### Scenario: Not a POST
- **WHEN** a test client requests the path with GET and the right token
- **THEN** the answer is 405

### Requirement: Accepting an import
The manifest view SHALL handle a manifest in one database transaction holding the lock (One lock):

1. When an import with the manifest's `build` exists, it answers as it answered that build and changes nothing.
2. When `outcome` is `refused`, it records a refused import with the manifest's errors, one per line, and answers 200 with `{"outcome": "refused", "import": <id>}`.
3. When `base` is not the id of the latest accepted import, or `null` while one exists, or names one while none exists, or when `snapshot` is not the `digest` of the registry's current snapshot (lab-registry "Snapshot"), it answers 409 with `{"outcome": "stale"}` and records nothing.
4. When the checks of Import checks find errors, it records a refused import with every error, in the order the checks find them, and answers likewise.
5. Otherwise it applies the manifest (Applying an import), records an accepted import, and answers 200 with `{"outcome": "accepted", "import": <id>}`.

The latest accepted import is the accepted import received last.

#### Scenario: First import
- **WHEN** the demo registry is loaded, no import exists, and a test posts the manifest of the demo collection, built against the current snapshot with `base` `null`
- **THEN** the answer is 200 with `accepted`, the import is accepted with the manifest's commit, release and language, and every procedure and sequence of the demo collection exists, none withdrawn

#### Scenario: A repeated build
- **WHEN** the test posts that manifest again, unchanged
- **THEN** the answer is the same, and no further import exists

#### Scenario: Stale base
- **WHEN** after the first import a test posts another manifest with `base` `null`
- **THEN** the answer is 409 with `stale` and only the first import exists

#### Scenario: Stale registry
- **WHEN** a test changes the note of `cinnamic-acid`, then posts a manifest built against the snapshot taken before
- **THEN** the answer is 409 with `stale` and no import is recorded for it

#### Scenario: A failed build
- **WHEN** a test posts a manifest with outcome `refused` and the errors `OSDB-0002.md:title: error: missing` and `build failed`
- **THEN** the answer is 200 with `refused`, the import is refused with those two lines as its errors, and the latest accepted import is unchanged

#### Scenario: After the demo's own import
- **WHEN** the demo data set is written and a test posts the demo collection's manifest with a real commit, built against the current snapshot with `base` the data set's import
- **THEN** the answer is 200 with `accepted`, and every task step of the data set names the same scope entry as before

### Requirement: Import checks
Before applying a built manifest, the application SHALL check it against its registry and its own content, and refuse it with one error for each of these, each beginning with the ID it concerns:

- an ID that occurs twice among the procedures or among the sequences: `<ID>: named twice`;
- a procedure's reaction type that the registry lacks: `<ID>: unknown reaction type "<key>"`;
- a substance key in an entry that the registry lacks: `<ID>: unknown substance "<key>"`;
- two entries of one procedure with the same signature: `<ID>: entries <n> and <m> have the signature <signature>`;
- a procedure with no entry: `<ID>: no entry`;
- a sequence target that the registry lacks: `<ID>: unknown target "<key>"`;
- a step naming a procedure the manifest does not hold: `<ID>: step <n> names <procedure>, which is not in the collection`;
- a step of a general procedure that gives no entry number or one that does not count one of its entries from 1, or a step of a specific procedure that gives one: `<ID>: step <n> names no entry of <procedure>`.

A refused import writes no procedure, entry or sequence.

#### Scenario: Unknown substance
- **WHEN** a test posts the demo manifest after replacing a product of `OSDB-0002` with `no-such-substance`
- **THEN** the import is refused with an error `OSDB-0002: unknown substance "no-such-substance"`, and no procedure exists

#### Scenario: One signature twice
- **WHEN** a test posts a manifest whose general procedure `OSDB-0009` has entries 1 and 3 with the same substrates and products
- **THEN** the import is refused with an error beginning `OSDB-0009: entries 1 and 3 have the signature`

#### Scenario: A step beyond the entries
- **WHEN** a test posts the demo manifest after setting the entry of the second step of `SEQ-0002` to 9
- **THEN** the import is refused with the error `SEQ-0002: step 2 names no entry of OSDB-0009`

### Requirement: Applying an import
Applying an accepted manifest SHALL make the rows match it:

- A procedure is matched by its ID, a sequence by its ID, and a scope entry, within its procedure, by its signature: the keys of its substrates sorted and joined by ` + `, then ` >> `, then the keys of its products sorted and joined by ` + `, as `4-bromoanisole + phenylboronic-acid >> 4-methoxybiphenyl`.
- A procedure or sequence the rows lack is created; one they have takes the manifest's values, `general` among them, and is no longer withdrawn; one the manifest lacks is withdrawn, its entries and steps left as they were.
- An entry of the manifest takes its position in the file and its substances' order and yields, and is no longer withdrawn; an entry the rows lack is created; an entry of the procedure whose signature the manifest lacks is withdrawn.
- A sequence's steps are replaced by the manifest's whenever they differ, each naming the entry the step resolves to: for a general procedure the entry its number counts from 1, for a specific procedure its only entry.
- A procedure's or sequence's `last_import` becomes the accepted import when it is created, or when any of its values, its entries or its steps change, withdrawing it or bringing it back included; otherwise it keeps the import it had.

#### Scenario: Yields change, the entry stays
- **WHEN** after the first import a test posts a manifest in which the yield of entry 1 of `OSDB-0009` changes from 90 to 92, with `base` the first import
- **THEN** the entry is the same row with the yield 92, and `OSDB-0009`'s `last_import` is the second import while `OSDB-0002`'s is still the first

#### Scenario: Substances change, the entry is new
- **WHEN** a test posts a manifest in which entry 1 of `OSDB-0009` has another substrate
- **THEN** `OSDB-0009` has a new entry with the new signature, and the entry with the old signature is withdrawn

#### Scenario: A file gone and back
- **WHEN** a test posts a manifest without `OSDB-0006`, which no sequence names, and then one with it again
- **THEN** after the first `OSDB-0006` is withdrawn, and after the second it is the same row, not withdrawn

#### Scenario: Steps follow the file
- **WHEN** a test posts a manifest in which `SEQ-0002` has a third step
- **THEN** `SEQ-0002` has three steps in the manifest's order and its `last_import` is the new one

### Requirement: One lock
`orgsyndb_web.lock.hold()` SHALL take, inside the current transaction, the one lock that serializes imports and the writes that change the snapshot's digest: on PostgreSQL by `SELECT pg_advisory_xact_lock(<key>)` with a fixed key, released when the transaction ends; on SQLite it does nothing. It raises an error outside a transaction. The manifest view takes it, and every save or deletion of a substance, of a term of the four vocabularies and of an article takes it in the transaction that writes, whatever path writes it: a form, the admin, a booking that numbers an article, `registry_load` and `registry_import`. A substance's chemical classes are set in the transaction that saves it.

#### Scenario: Registry writes take the lock
- **WHEN** a test replaces `hold` with a recorder and saves a substance through its form, a project through its form, a substance through the admin, an article's number through the delivery that gives it one, and runs `registry_load` on an empty registry
- **THEN** the recorder was called inside a transaction for each, before the write

#### Scenario: Outside a transaction
- **WHEN** a test calls `hold()` with autocommit on
- **THEN** it raises an error

### Requirement: Imports page
`/lab/collection/` SHALL need no sign-in and show the heading `Importe` (`Imports`) and, when an import was accepted, a line naming the latest accepted import's commit, its first ten digits, its release and its received time, and the number of procedures and of sequences not withdrawn. Below, a table lists the imports newest first with the columns `Empfangen` (`Received`), `Commit`, the first ten digits, `Anlass` (`Trigger`), as `Commit`, `Register` (`Registry`), `Werkzeuge` (`Tooling`) or `Nachholen` (`Catch-up`), `Ergebnis` (`Outcome`), as `Angenommen` (`Accepted`) or `Abgelehnt` (`Refused`), `Release`, and `Fehler` (`Errors`), a refused import's errors, one per line. Without imports the table is replaced by `Noch keine Importe.` (`No imports yet.`).

#### Scenario: Imports listed
- **WHEN** the demo data set is written, the demo manifest was accepted and a failed build was reported, and a test client that is not signed in requests `/lab/collection/`
- **THEN** the page answers 200, the table lists the refused import first with its errors and then the accepted one, and the line above names the accepted commit and the demo's numbers of procedures and sequences

#### Scenario: Nothing imported
- **WHEN** a test client requests `/lab/collection/` before any import
- **THEN** the page shows `Noch keine Importe.` and no table

