## MODIFIED Requirements

### Requirement: Products
The `products` field SHALL be a non-empty array of tables, one per product of the procedure, each holding:
- `compound`: a string that is the key of a substance of the collection's registry (compound-registry "Registry source");
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

### Requirement: Scheme image
The optional `scheme_image` field SHALL name an image of the procedure's reaction scheme, a relative path beginning with `structures/` and ending in `.svg` or `.png`, with no `..` component, naming a file that exists under the static directory, the wrong prefix or suffix leaving existence unchecked. Problems are reported under `scheme_image`, containing `must be a relative path under structures/` for the prefix or a `..` component, `must end in .svg or .png` for the suffix, and `not found` for a file that does not exist.

#### Scenario: Scheme image missing
- **WHEN** a general variant run sets `scheme_image = "structures/missing.svg"` under the file name `OSDB-0140-missing-scheme.md`
- **THEN** it reports exactly one error, field `scheme_image`, containing `not found`

### Requirement: Controlled reaction type
The `reaction_types` field SHALL be a list of exactly one string, and that string SHALL be a reaction type of the collection, a term of its registry's `reaction-types` (reaction-types "Reaction-type vocabulary"). A string that is not gets an error whose message contains `unknown reaction type "<v>"`.

#### Scenario: Reaction type outside the vocabulary
- **WHEN** a fixture run on `invalid/unknown-reaction-type` examines `OSDB-0111-unknown-reaction-type.md`, whose `reaction_types` is `["esterfication"]`
- **THEN** it reports exactly one error, field `reaction_types`, containing `unknown reaction type "esterfication"`

#### Scenario: Two reaction types
- **WHEN** a variant run sets `reaction_types = ["esterification", "reduction"]`, both in the fixture vocabulary, under the file name `OSDB-0100-two-reaction-types.md`
- **THEN** it reports exactly one error, field `reaction_types`, containing `must contain exactly one reaction type`

### Requirement: Markdown template
The file `templates/procedure.md` SHALL be a complete procedure using the placeholder ID `OSDB-0000` and slug `osdb-0000`. It satisfies the following:
- Its front matter explains every field in TOML comments and shows the optional fields commented out. The comment on `reaction_types` says that the allowed values are the reaction types of the registry, and no line of the template names `site/data` or `vocabularies/`.
- Its body has the eight sections, a Reagents table with the header `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, and numbered lists under Procedure and Notes.
- Its `products` names the compound key `example-compound`, and its commented-out `substrates` line names the same key.
- Once `OSDB-0000` is replaced by a real ID and `osdb-0000` by its lowercase form, it validates with no errors and no warnings against a registry that holds the substance `example-compound` and the reaction type the template names.

#### Scenario: Substituted Markdown template is clean
- **WHEN** a test copies `templates/procedure.md` to a temporary directory as `OSDB-0001-template.md`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, writes a snapshot holding the substance `example-compound` and the reaction type the template names, writes a settings file `orgsyndb.toml` holding `format = 1`, and runs the validator on that directory with `--registry` naming the snapshot and `--settings` naming that settings file
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Unsubstituted Markdown template is rejected
- **WHEN** a test copies `templates/procedure.md` unchanged to a temporary directory as `OSDB-0000-template.md` and runs the validator on it
- **THEN** the exit status is 1, and stdout contains an error with field `id` containing `must be between OSDB-0001 and OSDB-9999`

#### Scenario: The templates name the collection's reaction types
- **WHEN** a test reads `templates/procedure.md` and `templates/procedure.de.md`
- **THEN** each has a comment line before its `reaction_types` line that names the registry, and neither contains `site/data` or `vocabularies/`
