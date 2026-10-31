## MODIFIED Requirements

### Requirement: Compound fields
Every compound file SHALL hold a TOML table with these keys:
- `name`: non-empty string, the compound's name on an English site;
- `name_de`: optional non-empty string, its name on a German site (localization "German compound names");
- `formula`: non-empty string;
- `mw`: finite number greater than 0 (TOML integer or float, never boolean), in g/mol;
- `smiles`: non-empty string;
- `cas`: optional string matching `^\d{2,7}-\d{2}-\d$` whose final check digit verifies;
- `structure_image`: optional, as the requirement "Structure image path" states.

A missing required key is an error containing `required field missing`, and a value of the wrong type is an error. A compound file may also set the fields its collection declares, which compound-fields "Field values" checks. Any other key is a warning containing `unknown field`. Problems are reported on the compound file's path, under the key's name. The messages for `mw`, `cas` and `structure_image` are those the validator gave for the same checks of a procedure's former `product` table and `structure_image`: `must be a number in g/mol, unquoted, e.g. 88.11`, `must be greater than 0`, `must have the form NNNNNNN-NN-N, e.g. "64-17-5"`, `has a wrong check digit; check the number`, and those of the requirement below.

#### Scenario: Missing formula
- **WHEN** a registry variant run removes `formula` from `ethyl-acetate.toml`
- **THEN** it reports exactly one error, on the path ending `ethyl-acetate.toml`, field `formula`, containing `required field missing`

#### Scenario: Molecular weight of zero
- **WHEN** a registry variant run sets `mw = 0` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `mw`, containing `must be greater than 0`

#### Scenario: CAS number with a wrong check digit
- **WHEN** a registry variant run sets `cas = "141-78-5"` in `ethyl-acetate.toml` (the valid number is `141-78-6`)
- **THEN** it reports exactly one error, field `cas`, containing `check digit`

#### Scenario: Empty German name
- **WHEN** a registry variant run sets `name_de = ""` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `name_de`, containing `must not be empty`

#### Scenario: Misspelt key
- **WHEN** a registry variant run adds `smile = "CCOC(C)=O"` to `ethyl-acetate.toml`
- **THEN** it reports exactly one warning, field `smile`, containing `unknown field`

#### Scenario: A declared field is not unknown
- **WHEN** a field-declaration run adds `item_number = "CH-0001"` to `ethyl-acetate.toml`, with settings that declare the text field `item_number`
- **THEN** it reports no problem on `ethyl-acetate.toml`

### Requirement: Compound template
The file `templates/compound.toml` SHALL be a complete compound file that explains every key in TOML comments, sets every required key, and shows `name_de`, `cas` and `structure_image` commented out. It ends with comment lines saying that the fields a collection declares in its `orgsyndb.toml` are written below as further keys of the same form. Copied into a registry under a valid key, it validates with no error and no warning.

#### Scenario: Template validates
- **WHEN** a test copies `templates/compound.toml` into an empty temporary registry as `example-compound.toml` and runs the validator with that registry on an empty content root
- **THEN** it exits 0 and prints nothing to stdout
- **AND** the template's last comment block names `orgsyndb.toml`

