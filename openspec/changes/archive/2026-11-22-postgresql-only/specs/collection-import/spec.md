## MODIFIED Requirements

### Requirement: One lock
`orgsyndb_web.lock.hold()` SHALL take, inside the current transaction, the one lock that serializes imports and the writes that change the snapshot's digest, by `SELECT pg_advisory_xact_lock(<key>)` with a fixed key, released when the transaction ends. It raises an error outside a transaction. The manifest view, the ID view and `adopt_ids` (Issued IDs) take it, and every save or deletion of a substance, of a term of the four vocabularies, of an article, of a notebook and of an account takes it in the transaction that writes, except a save of only an account's fields the snapshot does not carry, such as a sign-in's last login, whatever path writes it: a form, the admin, a booking that numbers an article, `registry_load` and `registry_import`. A substance's chemical classes are set in the transaction that saves it.

#### Scenario: Registry writes take the lock
- **WHEN** a test replaces `hold` with a recorder and saves a substance through its form, a project through its form, a substance through the admin, an article's number through the delivery that gives it one, and runs `registry_load` on an empty registry
- **THEN** the recorder was called inside a transaction for each, before the write

#### Scenario: Outside a transaction
- **WHEN** a test calls `hold()` with autocommit on
- **THEN** it raises an error

#### Scenario: Account writes take the lock
- **WHEN** a test replaces `hold` with a recorder, renames an account, and then signs that account in
- **THEN** the recorder was called inside a transaction for the rename and not for the sign-in
