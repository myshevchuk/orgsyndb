## ADDED Requirements

### Requirement: Products
The `products` field SHALL be a non-empty array of tables, one per product of the procedure, each holding:
- `compound`: a string that is a key of the compound registry (compound-registry "Compound files");
- `yield_percent`: a finite number from 0 to 100 inclusive (TOML integer or float; never boolean), the yield of that product.

A problem inside the `n`-th table, counting from 1, is reported under `products[n].<key>`, and an entry that is not a table is an error under `products[n]` containing `must be a table`. Any other key in a table is a warning containing `unknown field`. The messages are:
- an empty array: `products` containing `must not be empty`; a value that is not an array: `products` containing `must be an array of tables`;
- a missing key: `required field missing`;
- a `compound` that is not a registry key: `unknown compound "<key>"`;
- a `yield_percent` that is not a number: `must be a number, unquoted, e.g. 85`; one outside the range: `<value> must be between 0 and 100`;
- a key named by two tables: one error under `products` containing `lists <key> twice`.

A procedure may have several products, each with its own yield.

#### Scenario: Unknown compound
- **WHEN** a fixture run on `invalid/unknown-compound` examines `OSDB-0123-unknown-compound.md`, whose only product names `no-such-compound`
- **THEN** it reports exactly one error, field `products[1].compound`, containing `unknown compound "no-such-compound"`

#### Scenario: Yield above 100
- **WHEN** a fixture run on `invalid/yield-out-of-range` examines `OSDB-0110-yield-out-of-range.md`, whose only product has `yield_percent = 104.5`
- **THEN** it reports exactly one error, field `products[1].yield_percent`, containing `must be between 0 and 100`

#### Scenario: Yield given as a string
- **WHEN** a variant run sets the product's `yield_percent = "85"` under the file name `OSDB-0100-yield-not-number.md`
- **THEN** it reports exactly one error, field `products[1].yield_percent`, containing `must be a number`

#### Scenario: Two products
- **WHEN** a variant run adds a second product `{ compound = "ethanol", yield_percent = 10 }` under the file name `OSDB-0100-two-products.md`
- **THEN** it exits 0 and prints nothing

#### Scenario: A product listed twice
- **WHEN** a variant run adds a second product naming the baseline's compound under the file name `OSDB-0100-product-twice.md`
- **THEN** it reports exactly one error, field `products`, containing `lists ethyl-acetate twice`

#### Scenario: No products
- **WHEN** a variant run sets `products = []` under the file name `OSDB-0100-no-products.md`
- **THEN** it reports exactly one error, field `products`, containing `must not be empty`

### Requirement: Substrates
The optional `substrates` field SHALL be a list of strings, the keys of the compounds the procedure starts from, each a key of the compound registry, none named twice and none among the procedure's own products. Problems are reported under `substrates`:
- a value that is not a list of strings: `must be a list of compound keys, e.g. ["ethanol"]`;
- a key not in the registry: `unknown compound "<key>"`;
- a key named twice: `lists <key> twice`;
- a key among the products: `<key> is also a product`.

#### Scenario: Unknown substrate
- **WHEN** a fixture run on `invalid/unknown-substrate` examines `OSDB-0124-unknown-substrate.md`, whose `substrates` is `["no-such-compound"]`
- **THEN** it reports exactly one error, field `substrates`, containing `unknown compound "no-such-compound"`

#### Scenario: A substrate that is also a product
- **WHEN** a variant run sets `substrates = ["ethyl-acetate"]`, the baseline's product, under the file name `OSDB-0100-substrate-is-product.md`
- **THEN** it reports exactly one error, field `substrates`, containing `ethyl-acetate is also a product`

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
- `products`: array of tables (requirement "Products")
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

### Requirement: Markdown template
The file `templates/procedure.md` SHALL be a complete procedure using the placeholder ID `OSDB-0000` and slug `osdb-0000`. It satisfies the following:
- Its front matter explains every field in TOML comments and shows the optional fields commented out.
- Its body has the eight sections, a Reagents table with the header `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, and numbered lists under Procedure and Notes.
- Its `products` names the compound key `example-compound`, and its commented-out `substrates` line names the same key.
- Once `OSDB-0000` is replaced by a real ID and `osdb-0000` by its lowercase form, it validates against the shipped vocabulary and a registry holding `templates/compound.toml` as `example-compound.toml` with no errors and no warnings.

#### Scenario: Substituted Markdown template is clean
- **WHEN** a test copies `templates/procedure.md` to a temporary directory as `OSDB-0001-template.md`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, copies `templates/compound.toml` into a temporary registry as `example-compound.toml`, and runs the validator on that directory with the default vocabulary and that registry
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Unsubstituted Markdown template is rejected
- **WHEN** a test copies `templates/procedure.md` unchanged to a temporary directory as `OSDB-0000-template.md` and runs the validator on it
- **THEN** the exit status is 1, and stdout contains an error with field `id` containing `must be between OSDB-0001 and OSDB-9999`

### Requirement: Org template
The file `templates/procedure.org` SHALL be a complete Org procedure that satisfies the following:
- It carries `#+CREATED` and `#+LAST_MODIFIED` in the required format.
- It sets `#+HUGO_SLUG: osdb-0000` and `#+HUGO_TAGS`.
- It sets the keys `id` (as `OSDB-0000`), `authors`, `status`, `reaction_types`, `scale`, `hazards` and `products` on repeated `#+HUGO_CUSTOM_FRONT_MATTER:` lines, `products` naming the compound key `example-compound`, and shows a `substrates` line commented out.
- It sets `products` alone on the last `#+HUGO_CUSTOM_FRONT_MATTER:` line, because tomelr emits keys in order and every key after a `[[products]]` table header would parse as a member of that table.
- It has the eight body sections as top-level headings, in order.
- It does not set `#+DATE`, `#+HUGO_LASTMOD`, `#+HUGO_AUTO_SET_LASTMOD`, `#+HUGO_DRAFT`, `#+HUGO_BASE_DIR` or `#+HUGO_SECTION`.

#### Scenario: Org template passes the Org checks
- **WHEN** an ERT test copies `templates/procedure.org` to a temporary directory as `OSDB-0001-template.org`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, and calls `osdb-org-examine` on that directory
- **THEN** it returns no problem and one source

#### Scenario: Org template carries the schema keywords and sections
- **WHEN** a test reads `templates/procedure.org`
- **THEN** it contains the line `#+HUGO_SLUG: osdb-0000` and a `#+HUGO_TAGS:` line
- **AND** the `#+HUGO_CUSTOM_FRONT_MATTER:` lines together contain `:id`, `:authors`, `:status`, `:reaction_types`, `:scale`, `:hazards` and `:products`
- **AND** the last `#+HUGO_CUSTOM_FRONT_MATTER:` line contains `:products` and no other `:key`, and no earlier such line contains `:products`
- **AND** its top-level headings, in order, include `* Summary`, `* Reagents`, `* Procedure`, `* Workup and Purification`, `* Characterization`, `* Notes`, `* Hazards and Waste Disposal` and `* References`
- **AND** no line begins, case-insensitively, with `#+DATE:`, `#+HUGO_LASTMOD:`, `#+HUGO_AUTO_SET_LASTMOD:`, `#+HUGO_DRAFT:`, `#+HUGO_BASE_DIR:` or `#+HUGO_SECTION:`

## REMOVED Requirements

### Requirement: Yield range
**Reason**: A procedure's yield now belongs to each of its products; the range check moves to the requirement "Products".
**Migration**: Give each entry of `products` its own `yield_percent`.

### Requirement: Product table
**Reason**: Compound data moves to the compound registry; a procedure names its products by key in `products`.
**Migration**: Move the `product` table's keys to `compounds/<key>.toml` and name the key in `products`.

### Requirement: Precursors refer to existing procedures
**Reason**: Precursors are derived from the compounds procedures share; a procedure names its starting materials in `substrates`.
**Migration**: Name the precursor's product in `substrates`.

### Requirement: Structure image path
**Reason**: A structure image belongs to a compound; the rule moves to compound-registry "Structure image path".
**Migration**: Set `structure_image` in the compound's registry file.
