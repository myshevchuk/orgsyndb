## MODIFIED Requirements

### Requirement: Import checks
Before applying a built manifest, the application SHALL check it against its registry and its own content, and refuse it with one error for each of these, each beginning with the ID it concerns:

- an ID that occurs twice among the procedures or among the sequences: `<ID>: named twice`;
- after the first accepted import, an ID the application has not issued (Issued IDs): `<ID>: not issued by the lab application`;
- a procedure's reaction type that the registry lacks: `<ID>: unknown reaction type "<key>"`;
- a procedure's `notebook` that is not `<code>/<number>`: `<ID>: notebook "<value>" is not <code>/<number>`; one whose code no notebook of the application has: `<ID>: unknown notebook "<code>"`; and one that another procedure of the manifest names too: `<ID>: notebook entry <entry> is also named by <other ID>`;
- a procedure's project that the registry lacks: `<ID>: unknown project "<key>"`;
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

#### Scenario: An unknown notebook
- **WHEN** a test posts the demo manifest after setting the `notebook` of `OSDB-0002` to `ZZ-9/1`
- **THEN** the import is refused with an error `OSDB-0002: unknown notebook "ZZ-9"`

#### Scenario: One entry, two procedures
- **WHEN** a test posts the demo manifest after setting the `notebook` of `OSDB-0003` to `AE-1/2`
- **THEN** the import is refused with the errors `OSDB-0002: notebook entry AE-1/2 is also named by OSDB-0003` and `OSDB-0003: notebook entry AE-1/2 is also named by OSDB-0002`

### Requirement: Imported rows
The lab application SHALL keep, in its package `collection`, these records:

- an import, one per build the builder reports: `build`, a UUID, unique; `commit`, the collection commit, 40 lowercase hexadecimal digits; `committed_at`; `base`, the accepted import it was built after, or none; `snapshot`, the registry digest it was built with, 64 lowercase hexadecimal digits; `tooling`, the application commit the builder ran, 40 lowercase hexadecimal digits; `release`, the release the builder staged for it, empty for a refused build; `language`, `de` or `en`, empty for a refused build; `outcome`, `accepted` or `refused`; `trigger`, `commit`, `registry`, `tooling` or `catch-up`; `errors`, one error per line, empty for an accepted import; and `received_at`;
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

### Requirement: Applying an import
Applying an accepted manifest SHALL make the rows match it:

- A procedure is matched by its ID, a sequence by its ID, and a scope entry, within its procedure, by its signature: the keys of its substrates sorted and joined by ` + `, then ` >> `, then the keys of its products sorted and joined by ` + `, as `4-bromoanisole + phenylboronic-acid >> 4-methoxybiphenyl`.
- A procedure or sequence the rows lack is created; one they have takes the manifest's values, `general` among them, and is no longer withdrawn; one the manifest lacks is withdrawn, its entries and steps left as they were.
- An entry of the manifest takes its position in the file and its substances' order and yields, and is no longer withdrawn; an entry the rows lack is created; an entry of the procedure whose signature the manifest lacks is withdrawn.
- A procedure's authors are replaced by the manifest's, in its order, whenever they differ.
- A procedure's `journal_entry` becomes the entry its `notebook` names, created in that notebook when it has no entry of that number, or none without a `notebook`; its `project` becomes the term its `project` names, or none. Both are among its values. A withdrawn procedure keeps its entry. Procedures the manifest lacks are withdrawn, and the entries of procedures whose entry changes are cleared, before any procedure takes a new entry or is brought back, so that an entry passes between procedures in one import.
- A sequence's steps are replaced by the manifest's whenever they differ, each naming the entry the step resolves to: for a general procedure the entry its number counts from 1, for a specific procedure its only entry.
- A procedure's or sequence's `last_import` becomes the accepted import when it is created, or when any of its values, its authors, its entries or its steps change, withdrawing it or bringing it back included; otherwise it keeps the import it had.

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

#### Scenario: Entries from the import
- **WHEN** the demo registry and notebooks are written, no import exists, and the demo collection's manifest is accepted
- **THEN** the procedure `OSDB-0002` names the entry `AE-1/2` and the project `first-year-practical`, and the notebook `AE-2` has the entries 7, 8, 11 and 12

#### Scenario: An entry passes to another procedure
- **WHEN** the demo collection was imported and a test posts its manifest without `OSDB-0002` and with the `notebook` of `OSDB-0003` set to `AE-1/2`
- **THEN** the import is accepted, `OSDB-0002` is withdrawn and still names `AE-1/2`, and `OSDB-0003` names `AE-1/2`

#### Scenario: Two procedures swap entries
- **WHEN** the demo collection was imported and a test posts its manifest with the notebooks of `OSDB-0002` and `OSDB-0003` swapped
- **THEN** the import is accepted, `OSDB-0002` names `AE-1/3` and `OSDB-0003` names `AE-1/2`

#### Scenario: A procedure returns with its entry
- **WHEN** after the import that passed `AE-1/2` to `OSDB-0003`, a test posts the demo manifest without `OSDB-0003`
- **THEN** the import is accepted, `OSDB-0002` is back and names `AE-1/2`, and `OSDB-0003` is withdrawn

### Requirement: One lock
`orgsyndb_web.lock.hold()` SHALL take, inside the current transaction, the one lock that serializes imports and the writes that change the snapshot's digest: on PostgreSQL by `SELECT pg_advisory_xact_lock(<key>)` with a fixed key, released when the transaction ends; on SQLite it does nothing. It raises an error outside a transaction. The manifest view, the ID view and `adopt_ids` (Issued IDs) take it, and every save or deletion of a substance, of a term of the four vocabularies, of an article, of a notebook and of an account takes it in the transaction that writes, except a save of only an account's fields the snapshot does not carry, such as a sign-in's last login, whatever path writes it: a form, the admin, a booking that numbers an article, `registry_load` and `registry_import`. A substance's chemical classes are set in the transaction that saves it.

#### Scenario: Registry writes take the lock
- **WHEN** a test replaces `hold` with a recorder and saves a substance through its form, a project through its form, a substance through the admin, an article's number through the delivery that gives it one, and runs `registry_load` on an empty registry
- **THEN** the recorder was called inside a transaction for each, before the write

#### Scenario: Outside a transaction
- **WHEN** a test calls `hold()` with autocommit on
- **THEN** it raises an error

#### Scenario: Account writes take the lock
- **WHEN** a test replaces `hold` with a recorder, renames an account, and then signs that account in
- **THEN** the recorder was called inside a transaction for the rename and not for the sign-in
