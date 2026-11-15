## MODIFIED Requirements

### Requirement: Imported rows
The lab application SHALL keep, in its package `collection`, these records:

- an import, one per build the builder reports: `build`, a UUID, unique; `commit`, the collection commit, 40 lowercase hexadecimal digits; `committed_at`; `base`, the accepted import it was built after, or none; `snapshot`, the registry digest it was built with, 64 lowercase hexadecimal digits; `tooling`, the application commit the builder ran, 40 lowercase hexadecimal digits; `release`, the release the builder staged for it, empty for a refused build; `language`, `de` or `en`, empty for a refused build; `outcome`, `accepted` or `refused`; `trigger`, `commit`, `registry`, `tooling` or `catch-up`; `pushed_by`, the account that pushed the commit (Manifest), or none; `errors`, one error per line, empty for an accepted import; and `received_at`;
- a procedure: `key`, its ID, an issued ID (Issued IDs), unique; `source`, `org` or `md`; `title`; `title_de`, which may be empty; `status`, `draft`, `checked` or `retired`, empty for a procedure no accepted import has given one; `reaction_type`, a reaction type of the registry; `general`, whether it is a general procedure; `journal_entry`, the journal entry it was written from (lab-journal "Notebooks and entries"), or none, no two procedures that are not withdrawn naming one; `project`, a term of the registry's projects, or none; `last_import`, the accepted import that created it or last changed it; and `withdrawn`;
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
