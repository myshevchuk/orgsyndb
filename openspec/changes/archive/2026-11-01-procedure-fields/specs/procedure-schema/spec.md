## MODIFIED Requirements

### Requirement: Keys outside the schema
Front-matter keys outside the schema SHALL be handled as follows:
- **Tolerated silently, subject to type:** `draft` (boolean `false` only), `description` (string), `aliases` (list of strings), `weight` (integer).
- **Errors:** `draft = true`, `author` and `url`.
- **Declared:** the key of a procedure field that the collection declares (procedure-fields "Procedure field declarations"), checked as procedure-fields "Procedure field values" states.
- **Warnings:** any other key, with a message containing `unknown field`.

#### Scenario: Draft set to true
- **WHEN** a variant run sets `draft = true` under the file name `OSDB-0100-draft-true.md`
- **THEN** it reports exactly one error, field `draft`, containing `use status, not draft`

#### Scenario: Singular author key
- **WHEN** a fixture run on `invalid/author-key` examines `OSDB-0129-author-key.md`, which has `author = ["A. Example"]` as well as a valid `authors`
- **THEN** it reports exactly one error, field `author`, containing `use authors`

#### Scenario: Explicit URL
- **WHEN** a variant run sets `url = "/procedures/osdb-0100/"` under the file name `OSDB-0100-url-key.md`
- **THEN** it reports exactly one error, field `url`, containing `derived from slug`

#### Scenario: Misspelt optional key
- **WHEN** a variant run sets `checkedby = ["B. Example"]` under the file name `OSDB-0100-unknown-key.md`
- **THEN** it reports exactly one warning, field `checkedby`, containing `unknown field`

#### Scenario: ox-hugo draft key passes
- **WHEN** the valid-set run examines `valid/export/OSDB-0003-*.md`, which has `draft = false` as ox-hugo emits it
- **THEN** no line is printed for that file

#### Scenario: A declared key is no unknown field
- **WHEN** a procedure-field run (procedure-fields "Procedure field fixture") sets `working_time = 2.5` in `OSDB-0100-baseline.md`, and a variant run sets the same key under the file name `OSDB-0100-undeclared.md`
- **THEN** the first exits 0 and prints nothing to stdout, and the second reports exactly one warning, field `working_time`, containing `unknown field`
