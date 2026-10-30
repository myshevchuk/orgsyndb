## ADDED Requirements

### Requirement: Scheme image
The optional `scheme_image` field SHALL name an image of the procedure's reaction scheme, with the rules of compound-registry "Structure image path": a relative path beginning with `structures/` and ending in `.svg` or `.png`, with no `..` component, naming a file that exists under the static directory, the wrong prefix or suffix leaving existence unchecked. Problems are reported under `scheme_image` with that requirement's messages.

#### Scenario: Scheme image missing
- **WHEN** a general variant run sets `scheme_image = "structures/missing.svg"` under the file name `OSDB-0140-missing-scheme.md`
- **THEN** it reports exactly one error, field `scheme_image`, containing `not found`

## MODIFIED Requirements

### Requirement: Required front-matter fields
Every procedure SHALL carry, in its TOML front matter, each of the following keys with the stated type. A missing key is an error containing `required field missing`, and a value of the wrong TOML type is an error.
- `id`: string
- `slug`: string
- `title`: non-empty string, the procedure's heading, usually naming what it makes
- `date`: offset datetime
- `lastmod`: offset datetime
- `authors`: non-empty list of non-empty strings
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
