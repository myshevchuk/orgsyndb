## MODIFIED Requirements

### Requirement: Required front-matter fields
Every procedure SHALL carry, in its TOML front matter, each of the following keys with the stated type. A missing key is an error containing `required field missing`, and a value of the wrong TOML type is an error.
- `id`: string
- `slug`: string
- `title`: non-empty string, the procedure's heading, usually naming what it makes
- `date`: offset datetime
- `lastmod`: offset datetime
- `authors`: non-empty list of user names of the registry's accounts (procedure-authors "Authors are accounts")
- `status`: string
- `reaction_types`: list of strings
- `tags`: non-empty list of strings
- `products`: array of tables (requirement "Products"), except in a general procedure, which carries `scope` instead (general-procedures "Scope entries")
- `scale`: string
- `hazards`: non-empty list of non-empty strings

#### Scenario: Missing title
- **WHEN** a fixture run on `invalid/missing-title` examines `OSDB-0101-missing-title.md`, which has no `title` key
- **THEN** it reports exactly one error, field `title`, containing `required field missing`

#### Scenario: Empty hazards list
- **WHEN** a variant run sets `hazards = []` under the file name `OSDB-0100-empty-hazards.md`
- **THEN** it reports exactly one error, field `hazards`, containing `must not be empty`

#### Scenario: Empty tags list
- **WHEN** a variant run sets `tags = []` under the file name `OSDB-0100-empty-tags.md`
- **THEN** it reports exactly one error, field `tags`, containing `must not be empty`
