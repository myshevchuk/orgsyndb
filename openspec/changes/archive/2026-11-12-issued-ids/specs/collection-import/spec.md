## ADDED Requirements

### Requirement: Issued IDs
The application SHALL issue the IDs of procedures, `OSDB-NNNN`, and of sequences, `SEQ-NNNN`, and keep each issued ID once, with the account it was issued to, none for an adopted one, and when it was issued (Imported rows). Issuing and adopting take the lock (One lock).

- `POST /lab/collection/ids/` with a body `{"kind": "procedure"}` or `{"kind": "sequence"}` and an access token (web-app "Access tokens") issues to the token's account the ID of that kind one above the highest issued one, and answers 201 with `{"id": <ID>}`. A request without a valid token answers 401, whether or not it carries a signed-in session; a body of another shape 400; a request made before the application has accepted an import, or for a kind whose ID `9999` is issued, 409 with `{"error": <message>}`. None of them issues anything. The path is exempt from CSRF checks, never redirects and answers JSON.
- The first import the application accepts adopts every ID that its manifest names under `procedures`, `sequences` and `deleted` (Manifest) and that is not issued. A refused import adopts nothing. Later imports adopt nothing and ignore `deleted`; they refuse an ID that is not issued (Import checks).
- `manage.py adopt_ids ID...` adopts each named ID that is not issued, printing `adopted <ID>`, prints `<ID> was issued` for one that was, and exits 0. It exits 1, adopting nothing, with a message naming the first argument that is not a procedure or sequence ID, and is a usage error without arguments.
- The admin lists issued IDs for staff, read-only.

#### Scenario: Two IDs in turn
- **WHEN** the demo data set is written and user `klehmann` requests a procedure ID with a token, and then user `tbauer` does
- **THEN** the answers are `OSDB-0010` and `OSDB-0011`, the first issued to `klehmann` and the second to `tbauer`

#### Scenario: A sequence ID
- **WHEN** the demo data set is written and a client requests a sequence ID with a token
- **THEN** the answer is `SEQ-0003`

#### Scenario: Not before an import
- **WHEN** the demo registry is loaded, no import exists, and user `klehmann` requests a procedure ID with a token
- **THEN** the answer is 409 and no ID is issued

#### Scenario: A session is not a token
- **WHEN** the demo data set is written and a client signed in as `klehmann` posts `{"kind": "procedure"}` to `/lab/collection/ids/` without a token
- **THEN** the answer is 401 and no ID is issued to `klehmann`

#### Scenario: Adopted by the first accepted import
- **WHEN** the demo registry is loaded, no import exists, a manifest that names an unknown substance is refused, and then the demo collection's manifest with `deleted` set to `["OSDB-0012"]` is accepted
- **THEN** `OSDB-0001` to `OSDB-0009`, `OSDB-0012`, `SEQ-0001` and `SEQ-0002` are issued, to no account, and the next procedure ID issued is `OSDB-0013`

#### Scenario: Adopting by hand
- **WHEN** the demo data set is written and an operator runs `manage.py adopt_ids OSDB-0012 OSDB-0003`, and then a test posts the demo manifest with an added procedure `OSDB-0012`
- **THEN** the command prints `adopted OSDB-0012` and `OSDB-0003 was issued`, and the import is accepted
- **AND** `manage.py adopt_ids OSDB-12` exits 1 and adopts nothing

## MODIFIED Requirements

### Requirement: Import checks
Before applying a built manifest, the application SHALL check it against its registry and its own content, and refuse it with one error for each of these, each beginning with the ID it concerns:

- an ID that occurs twice among the procedures or among the sequences: `<ID>: named twice`;
- after the first accepted import, an ID the application has not issued (Issued IDs): `<ID>: not issued by the lab application`;
- a procedure's reaction type that the registry lacks: `<ID>: unknown reaction type "<key>"`;
- an author whose user name no account has: `<ID>: unknown author "<name>"`;
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

#### Scenario: Unknown author
- **WHEN** a test posts the demo manifest after setting the authors of `OSDB-0002` to `["nobody"]`
- **THEN** the import is refused with an error `OSDB-0002: unknown author "nobody"`

#### Scenario: An ID not issued
- **WHEN** the demo collection was imported and a test posts its manifest with an added procedure `OSDB-0010` that nobody took
- **THEN** the import is refused with the error `OSDB-0010: not issued by the lab application`, and after user `klehmann` takes `OSDB-0010` the manifest, posted again as a new build, is accepted

### Requirement: Imported rows
The lab application SHALL keep, in its package `collection`, these records:

- an import, one per build the builder reports: `build`, a UUID, unique; `commit`, the collection commit, 40 lowercase hexadecimal digits; `committed_at`; `base`, the accepted import it was built after, or none; `snapshot`, the registry digest it was built with, 64 lowercase hexadecimal digits; `tooling`, the application commit the builder ran, 40 lowercase hexadecimal digits; `release`, the release the builder staged for it, empty for a refused build; `language`, `de` or `en`, empty for a refused build; `outcome`, `accepted` or `refused`; `trigger`, `commit`, `registry`, `tooling` or `catch-up`; `errors`, one error per line, empty for an accepted import; and `received_at`;
- a procedure: `key`, its ID, an issued ID (Issued IDs), unique; `source`, `org` or `md`; `title`; `title_de`, which may be empty; `reaction_type`, a reaction type of the registry; `general`, whether it is a general procedure; `last_import`, the accepted import that created it or last changed it; and `withdrawn`;
- a procedure author: its `procedure`; a `user`, an account; and `position`, its place among the procedure's authors, from 1, each account once per procedure;
- a scope entry: its `procedure`; `signature` (Applying an import), unique within the procedure; `position`, from 1; and `withdrawn`;
- an entry substance: its `entry`; a `substance` of the registry; `role`, `substrate` or `product`; `yield_percent`, for a product only, which may be none; and `position`, its place among the entry's substances of that role, from 1, each substance once per role;
- a sequence: `key`, its ID, an issued ID, unique; `title`; `title_de`, which may be empty; `target`, a substance; `last_import`; and `withdrawn`;
- a step: its `sequence`; `position`, from 1, unique within the sequence; and `entry`, a scope entry.
- an issued ID: `key`, an `OSDB-NNNN` or `SEQ-NNNN`, unique; `user`, the account it was issued to, or none for an adopted ID; and `issued_at`.

Only the manifest view (Accepting an import) writes them, the ID view and `adopt_ids` writing issued IDs (Issued IDs), and the demo data command, which records the data set's own import the same way (lab-demo "Demo data command"). Tasks name a sequence and their steps name scope entries and imports (task-tracker "Task record"). An import never deletes a procedure, scope entry or sequence; a substance, reaction type, scope entry or account that a row names cannot be deleted, and only `demo_data --replace` deletes these records, with the other lab records (lab-demo "Demo data command"). The admin lists imports, procedures, sequences and issued IDs for staff, read-only, with no way to add, change or delete one.

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
- for `built`, `release`: a non-empty string, and `language`, `procedures`, `sequences` and `deleted` as `tools/orgsyndb manifest` prints them (build-script "manifest subcommand").

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

### Requirement: One lock
`orgsyndb_web.lock.hold()` SHALL take, inside the current transaction, the one lock that serializes imports and the writes that change the snapshot's digest: on PostgreSQL by `SELECT pg_advisory_xact_lock(<key>)` with a fixed key, released when the transaction ends; on SQLite it does nothing. It raises an error outside a transaction. The manifest view, the ID view and `adopt_ids` (Issued IDs) take it, and every save or deletion of a substance, of a term of the four vocabularies, of an article and of an account takes it in the transaction that writes, except a save of only an account's fields the snapshot does not carry, such as a sign-in's last login, whatever path writes it: a form, the admin, a booking that numbers an article, `registry_load` and `registry_import`. A substance's chemical classes are set in the transaction that saves it.

#### Scenario: Registry writes take the lock
- **WHEN** a test replaces `hold` with a recorder and saves a substance through its form, a project through its form, a substance through the admin, an article's number through the delivery that gives it one, and runs `registry_load` on an empty registry
- **THEN** the recorder was called inside a transaction for each, before the write

#### Scenario: Outside a transaction
- **WHEN** a test calls `hold()` with autocommit on
- **THEN** it raises an error

#### Scenario: Account writes take the lock
- **WHEN** a test replaces `hold` with a recorder, renames an account, and then signs that account in
- **THEN** the recorder was called inside a transaction for the rename and not for the sign-in
