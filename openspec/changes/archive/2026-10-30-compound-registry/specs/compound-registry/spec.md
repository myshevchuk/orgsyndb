## ADDED Requirements

### Requirement: Compound files
A collection's compound registry SHALL be its directory `compounds/`, holding one file per compound named `<key>.toml`, where `<key>` matches `^[a-z0-9]+(-[a-z0-9]+)*$` and is the compound's key. The key is the compound's identity: a procedure names a compound by its key, and two procedures name the same compound exactly when they name the same key. The validator reads the registry from the directory its `--compounds` option names (procedure-validation "Command-line interface"):
- A file whose name begins with `.` is skipped silently.
- A subdirectory is a `file_name` error on its path, containing `subdirectories are not supported`; its contents are not read.
- Any other file whose name is not `<key>.toml` is a `file_name` error containing `must be named <key>.toml, the key lowercase and hyphenated`, and defines no compound.
- A file that is not UTF-8 or is not valid TOML gets one `toml` error, containing `invalid TOML` for a parse error, and defines no compound.

A compound that no procedure names is allowed and draws no problem.

#### Scenario: Badly named compound file
- **WHEN** a registry variant run adds `Ethyl_Acetate.toml`, a copy of `ethyl-acetate.toml`, to the registry
- **THEN** it reports exactly one error, on the path ending `Ethyl_Acetate.toml`, field `file_name`, containing `must be named <key>.toml`

#### Scenario: Unparseable compound file
- **WHEN** a registry variant run replaces the text of `ethyl-acetate.toml` with `name = "Ethyl acetate`
- **THEN** it reports exactly one error, on the path ending `ethyl-acetate.toml`, field `toml`, containing `invalid TOML`, and one error for each procedure of the run that names `ethyl-acetate`, containing `unknown compound "ethyl-acetate"`

#### Scenario: Dotfiles and unused compounds
- **WHEN** a registry variant run adds `.gitkeep` and `unused-compound.toml`, a valid compound that no procedure names, to the registry
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Compound fields
Every compound file SHALL hold a TOML table with these keys:
- `name`: non-empty string, the compound's name on an English site;
- `name_de`: optional non-empty string, its name on a German site (localization "German compound names");
- `formula`: non-empty string;
- `mw`: finite number greater than 0 (TOML integer or float, never boolean), in g/mol;
- `smiles`: non-empty string;
- `cas`: optional string matching `^\d{2,7}-\d{2}-\d$` whose final check digit verifies;
- `structure_image`: optional, as the requirement "Structure image path" states.

A missing required key is an error containing `required field missing`, and a value of the wrong type is an error. Any other key is a warning containing `unknown field`. Problems are reported on the compound file's path, under the key's name. The messages for `mw`, `cas` and `structure_image` are those the validator gave for the same checks of a procedure's former `product` table and `structure_image`: `must be a number in g/mol, unquoted, e.g. 88.11`, `must be greater than 0`, `must have the form NNNNNNN-NN-N, e.g. "64-17-5"`, `has a wrong check digit; check the number`, and those of the requirement below.

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

### Requirement: Structure image path
The optional `structure_image` of a compound SHALL be a relative path beginning with `structures/` and ending in `.svg` or `.png`, with no `..` component, naming a file that exists under the static directory. A path with the wrong prefix or suffix is not checked for existence.

#### Scenario: Image file missing
- **WHEN** a registry variant run sets `structure_image = "structures/missing.svg"` in `ethyl-acetate.toml`, a file absent from `tests/fixtures/static`
- **THEN** it reports exactly one error, field `structure_image`, containing `not found`

#### Scenario: Unsupported image type
- **WHEN** a registry variant run sets `structure_image = "structures/ethyl-acetate.jpg"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `structure_image`, containing `must end in .svg or .png`

#### Scenario: Image outside the structures directory
- **WHEN** a registry variant run sets `structure_image = "ethyl-acetate.svg"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `structure_image`, containing `must be a relative path under structures/`

### Requirement: Compound template
The file `templates/compound.toml` SHALL be a complete compound file that explains every key in TOML comments, sets every required key, and shows `name_de`, `cas` and `structure_image` commented out. Copied into a registry under a valid key, it validates with no error and no warning.

#### Scenario: Template validates
- **WHEN** a test copies `templates/compound.toml` into an empty temporary registry as `example-compound.toml` and runs the validator with that registry on an empty content root
- **THEN** it exits 0 and prints nothing to stdout
