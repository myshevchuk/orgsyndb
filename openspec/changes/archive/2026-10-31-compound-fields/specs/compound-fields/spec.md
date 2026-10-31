## ADDED Requirements

### Requirement: Field declarations
A collection SHALL declare the fields its compounds carry beyond those of compound-registry "Compound fields" in its `orgsyndb.toml`, as the array of tables `fields.compound`, one table per field, in the order the site shows them. `fields`, when present, is a table whose only key is `compound`. A collection whose `orgsyndb.toml` has no `fields` declares no field. Each declaration holds:
- `key`: required. It matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, is none of the compound-registry keys `name`, `name_de`, `formula`, `mw`, `smiles`, `cas` and `structure_image`, does not end in `_de`, and no other declaration has it. A compound file sets the field under this key.
- `type`: required; `text`, `number`, `boolean` or `choice`.
- `label`: required non-empty string, the field's name on an English site. `label_de`: optional non-empty string, its name on a German site, which shows `label` when it is absent.
- `required`: optional boolean, default `false`. When `true`, every compound sets the field.
- `column`: optional boolean, default `false`. When `true`, the compound directory shows the field as a column (site-theme "Compound directory").
- For `text`: `pattern`, an optional string holding a Python regular expression that the whole value matches; and `unique`, an optional boolean, default `false`, under which no two compounds set the same value.
- For `number`: `min` and `max`, optional finite numbers (TOML integer or float, never boolean) bounding the value inclusively, `min` not greater than `max`; `unit`, an optional non-empty string written after the value; and `unique` as for `text`.
- For `choice`: `vocabulary`, required, the name of a vocabulary of the collection (requirement "Vocabularies"); and `multiple`, an optional boolean, default `false`, under which a compound sets a list of values rather than one.

A declaration holds no other key, and no key that its type does not take.

#### Scenario: The fixture declarations are accepted
- **WHEN** a field-declaration run makes no change
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Vocabularies
A vocabulary SHALL be the file `vocabularies/<name>.toml` in the directory of the collection's `orgsyndb.toml`, where `<name>` matches `^[a-z0-9]+(-[a-z0-9]+)*$`. Each top-level key of the file is a value of the vocabulary and matches the same pattern. Its table holds:
- `label`: required non-empty string, the value's name on an English site;
- `label_de`: optional non-empty string, its name on a German site, which shows `label` when it is absent;
- `parent`: optional, another value of the same vocabulary, under which this value is filed.

Following `parent` from any value ends at a value without one, a top-level value; the values passed on the way are the value's ancestors, and no value is its own ancestor. An entry holds no other key, and a vocabulary has at least one value. A vocabulary that no declaration names is not read.

#### Scenario: Values at every level
- **WHEN** a field-declaration run sets `chemical_class = ["carbonyl-compounds", "ketones"]` and `storage = "fridge"` in `ethyl-acetate.toml`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Declaration errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr when the settings file it reads (procedure-validation "Command-line interface") was named by `--settings` and does not exist, cannot be read as UTF-8 TOML, breaks the rules of collection "Collection layout" for `format` and the top-level keys, or breaks a rule of the requirements "Field declarations" or "Vocabularies". In particular this holds when:
- `fields` is not a table or holds a key other than `compound`, or `fields.compound` is not an array of tables;
- a declaration lacks `key`, `type` or `label`, has a value of the wrong type, or holds a key that is unknown or that its type does not take;
- a `key` breaks its pattern, names a compound-registry key, ends in `_de`, or is declared twice;
- a `pattern` is not a valid Python regular expression, `min` or `max` is not finite, or `min` is greater than `max`;
- the vocabulary a `choice` field names does not exist or cannot be read as UTF-8 TOML;
- a vocabulary has a key that is not a slug, an entry that is not a table with a non-empty string `label`, an empty or non-string `label_de`, a `parent` that is not one of its values, a value that is its own ancestor, an entry key other than `label`, `label_de` and `parent`, or no value.

The message names the settings file or the vocabulary file, the field's key when the declaration has a valid one, and the offending key or value.

#### Scenario: An option the type does not take
- **WHEN** a field-declaration run adds `pattern = "x"` to the declaration of `stock`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:`, `stock` and `pattern`

#### Scenario: An unknown option
- **WHEN** a field-declaration run adds `facet = true` to the declaration of `chemical_class`
- **THEN** it exits 2, stdout is empty, and stderr contains `chemical_class` and `facet`

#### Scenario: A built-in key
- **WHEN** a field-declaration run adds a declaration with `key = "cas"`, `type = "text"` and `label = "CAS"`
- **THEN** it exits 2, and stderr contains `cas`

#### Scenario: A missing vocabulary
- **WHEN** a field-declaration run sets `vocabulary = "no-such-vocabulary"` in the declaration of `storage`
- **THEN** it exits 2, and stderr contains `no-such-vocabulary`

#### Scenario: A value filed under itself
- **WHEN** a field-declaration run adds `parent = "ketones"` to the value `carbonyl-compounds` of `vocabularies/chemical-classes.toml`
- **THEN** it exits 2, and stderr contains `chemical-classes` and `parent`

#### Scenario: A pattern that does not compile
- **WHEN** a field-declaration run sets `pattern = "CH-("` in the declaration of `item_number`
- **THEN** it exits 2, and stderr contains `item_number` and `pattern`

#### Scenario: A bound that is not a number
- **WHEN** a field-declaration run adds `max = nan` to the declaration of `stock`
- **THEN** it exits 2, and stderr contains `stock` and `max`

#### Scenario: A misspelt top-level key
- **WHEN** a field-declaration run replaces every `[[fields.compound]]` of its `orgsyndb.toml` with `[[feilds.compound]]`
- **THEN** it exits 2, and stderr contains `feilds`

#### Scenario: A named settings file that does not exist
- **WHEN** a fixture run on `baseline` adds `--settings tests/fixtures/no-such-settings.toml`
- **THEN** it exits 2, stdout is empty, and stderr contains `no-such-settings.toml`

#### Scenario: A single table instead of an array
- **WHEN** a test runs the validator with `--settings` naming a settings file that holds `format = 1` and one `[fields.compound]` table with `key`, `type` and `label`
- **THEN** it exits 2, and stderr contains `fields.compound`

### Requirement: Field values
For each field its collection declares, the validator SHALL check the value that a compound file sets under the field's key, and report each problem on the compound file's path under that key:
- A compound file that does not set a field declared `required` gets an error containing `required field missing`.
- `text`: a non-empty string (`must be a string`, `must not be empty`) that, when the field declares `pattern`, matches it as a whole (`must match the pattern <pattern>`).
- `number`: a finite TOML integer or float, never a boolean (`must be a number, unquoted`), not less than `min` (`must be at least <min>`) and not greater than `max` (`must be at most <max>`).
- `boolean`: `true` or `false` (`must be true or false, unquoted`).
- `choice`: a string (`must be a string`) that is a value of the field's vocabulary (`unknown value "<v>"; see vocabularies/<name>.toml for the allowed values`). Under `multiple`, a non-empty list of strings (`must be a list of strings, e.g. ["<a value>"]`, `must not be empty`), each a value of the vocabulary, with one `unknown value` error per string that is not, and none repeated (`repeats "<v>"`).

A value of the wrong type draws that one error and no other. A choice may name any value of its vocabulary, a top-level value or one filed under another. When a field is declared `unique`, every value that passes these checks and is set by more than one compound draws an error on each of those compound files, containing `also set by` and the keys of the other compounds. A compound file that does not parse sets no value.

#### Scenario: A text value that breaks its pattern
- **WHEN** a field-declaration run sets `item_number = "CH-12"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, on the path ending `ethyl-acetate.toml`, field `item_number`, containing `must match the pattern`

#### Scenario: A value set twice under a unique field
- **WHEN** a field-declaration run sets `item_number = "CH-0001"` in `ethyl-acetate.toml` and in `ethanol.toml`
- **THEN** it exits 1 and reports exactly two problems, both errors with field `item_number` containing `also set by`, one on each file, the one on `ethanol.toml` naming `ethyl-acetate` and the other naming `ethanol`

#### Scenario: A number below its minimum
- **WHEN** a field-declaration run sets `stock = -1` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `stock`, containing `must be at least 0`

#### Scenario: A quoted number
- **WHEN** a field-declaration run sets `stock = "5"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `stock`, containing `must be a number`

#### Scenario: A quoted boolean
- **WHEN** a field-declaration run sets `in_house = "yes"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `in_house`, containing `must be true or false`

#### Scenario: A value outside the vocabulary
- **WHEN** a field-declaration run sets `storage = "freezer"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `storage`, containing `unknown value "freezer"` and `vocabularies/storage.toml`

#### Scenario: One value where a list is declared
- **WHEN** a field-declaration run sets `chemical_class = "esters"` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `chemical_class`, containing `must be a list of strings`

#### Scenario: A repeated value
- **WHEN** a field-declaration run sets `chemical_class = ["esters", "esters"]` in `ethyl-acetate.toml`
- **THEN** it reports exactly one error, field `chemical_class`, containing `repeats "esters"`

#### Scenario: A required field
- **WHEN** a field-declaration run adds `required = true` to the declaration of `storage`
- **THEN** it exits 1 and reports one error per compound file of the fixture registry and no other problem, each with field `storage` and containing `required field missing`

### Requirement: Field data for the site
`pipeline.fields_data(settings, language)` SHALL return the field data that the build stages as `build/data/fields.json` (build-script "build subcommand"), given the path of the collection's settings file and the site's language. The data is a table whose only key is `compound`, holding one table per declaration of `fields.compound`, in declared order, each with these keys and no other:
- `key`, `type` and `column`, as declared, `column` with its default;
- `label`: the field's shown label, its `label_de` on a German site when it declares one, and its `label` otherwise;
- `unit`: only for a `number` field that declares one, as declared;
- `multiple`: only for a `choice` field, as declared, with its default;
- `values`: only for a `choice` field, a table holding every value of its vocabulary under the value's key, each a table of `label`, the value's shown label, chosen as the field's is, and `path`, the shown labels of the value's ancestors, outermost first, followed by its own.

A settings file that does not exist, or that declares no field, gives `{"compound": []}`. A settings file that breaks a rule of the requirements "Field declarations" or "Vocabularies" raises `validate.ConfigError`.

#### Scenario: Field data in both languages
- **WHEN** a test calls `fields_data` on `tests/fixtures/fields/orgsyndb.toml` with the language `en`, and again with `de`
- **THEN** each lists the six fixture fields in declared order with the stated keys, `stock` has the `unit` `g`, `chemical_class` has `multiple` `true` and `column` `true`, and `storage` has `multiple` `false`
- **AND** in `en` the value `ketones` of `chemical_class` has the label `Ketones` and the path `["Carbonyl compounds", "Ketones"]`, and in `de` the label `Ketone` and the path `["Carbonylverbindungen", "Ketone"]`
- **AND** `short_name`, which declares no `label_de`, has the label `Short name` in both

#### Scenario: No settings file
- **WHEN** a test calls `fields_data` on a path that does not exist
- **THEN** it returns `{"compound": []}`

### Requirement: Field display
The site SHALL name a declared field by its shown label (requirement "Field data for the site") and write a compound's value of it as text, escaped once, as follows:
- `text`: the value;
- `number`: the value written as the compound facts write the molecular weight, with the language's decimal separator, followed by a space and the `unit` when the field declares one;
- `boolean`: `Yes` or `No`, on a German site `Ja` or `Nein`;
- `choice`: on a compound page, the labels of each value's `path` joined by ` › `; in the compound directory, each value's own label. Several values are written in the compound's order, separated by `, `.

#### Scenario: Declared fields in English
- **WHEN** a test scans every compound page and the compound directory after a theme build in locale `en`
- **THEN** each value of a declared field that a compound sets is written as stated, computed from the registry and the field data of the test collection's `orgsyndb.toml`

#### Scenario: Declared fields in German
- **WHEN** a test reads the compound pages of a build of the test collection in locale `de`
- **THEN** the declared fields carry their German labels, a `stock` value that is not a whole number is written with a decimal comma followed by ` g`, `in_house` reads `Ja` or `Nein`, and a chemical class reads as the German labels of its path joined by ` › `

#### Scenario: Markup in a label or a value is text
- **WHEN** a test builds a copy of the test collection in locale `en` after setting the `label` of `short_name` in its `orgsyndb.toml` to `Name <b>&</b>` and the `short_name` of `acetone` to `<i>Me</i>2CO & co`
- **THEN** the facts of the page of `acetone` hold a `dt` whose text is `Name <b>&</b>` and a `dd` whose text is `<i>Me</i>2CO & co`, and no `b` or `i` element
