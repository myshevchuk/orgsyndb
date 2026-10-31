## MODIFIED Requirements

### Requirement: Field declarations
A collection SHALL declare the fields its compounds carry beyond those of compound-registry "Compound fields" in its `orgsyndb.toml`, as the array of tables `fields.compound`, one table per field, in the order the site shows them. `fields`, when present, is a table whose only key is `compound`. A collection whose `orgsyndb.toml` has no `fields` declares no field. Each declaration holds:
- `key`: required. It matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, is none of the compound-registry keys `name`, `name_de`, `formula`, `mw`, `smiles`, `cas` and `structure_image`, is none of `id`, `title`, `created`, `modified`, `text`, `q`, `sort` and `view`, which the compound catalogue uses for its rows and its address (site-catalogue "Compound catalogue"), does not end in `_de`, and no other declaration has it. A compound file sets the field under this key.
- `type`: required; `text`, `number`, `boolean` or `choice`.
- `label`: required non-empty string, the field's name on an English site. `label_de`: optional non-empty string, its name on a German site, which shows `label` when it is absent.
- `required`: optional boolean, default `false`. When `true`, every compound sets the field.
- `column`: optional boolean, default `false`. When `true`, the compound directory shows the field as a column (site-theme "Compound directory").
- For `text`: `pattern`, an optional string holding a Python regular expression that the whole value matches; `unique`, an optional boolean, default `false`, under which no two compounds set the same value; and `search`, an optional boolean, default `false`, under which the compound catalogue's search matches the field's values.
- For `number`: `min` and `max`, optional finite numbers (TOML integer or float, never boolean) bounding the value inclusively, `min` not greater than `max`; `unit`, an optional non-empty string written after the value; and `unique` as for `text`.
- For `boolean`: `facet`, an optional boolean, default `false`, under which the compound catalogue offers the field as a filter.
- For `choice`: `vocabulary`, required, the name of a vocabulary of the collection (requirement "Vocabularies"); `multiple`, an optional boolean, default `false`, under which a compound sets a list of values rather than one; and `facet` as for `boolean`.

A declaration holds no other key, and no key that its type does not take.

#### Scenario: The fixture declarations are accepted
- **WHEN** a field-declaration run makes no change
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Facets and search where the types take them
- **WHEN** a field-declaration run adds `facet = true` to the declarations of `chemical_class`, `storage` and `in_house`, and `search = true` to those of `item_number` and `short_name`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Declaration errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr when the settings file it reads (procedure-validation "Command-line interface") was named by `--settings` and does not exist, cannot be read as UTF-8 TOML, breaks the rules of collection "Collection layout" for `format` and the top-level keys, or breaks a rule of the requirements "Field declarations" or "Vocabularies". In particular this holds when:
- `fields` is not a table or holds a key other than `compound`, or `fields.compound` is not an array of tables;
- a declaration lacks `key`, `type` or `label`, has a value of the wrong type, or holds a key that is unknown or that its type does not take;
- a `key` breaks its pattern, names a compound-registry key or a key the compound catalogue reserves, ends in `_de`, or is declared twice;
- a `pattern` is not a valid Python regular expression, `min` or `max` is not finite, or `min` is greater than `max`;
- the vocabulary a `choice` field names does not exist or cannot be read as UTF-8 TOML;
- a vocabulary has a key that is not a slug, an entry that is not a table with a non-empty string `label`, an empty or non-string `label_de`, a `parent` that is not one of its values, a value that is its own ancestor, an entry key other than `label`, `label_de` and `parent`, or no value.

The message names the settings file or the vocabulary file, the field's key when the declaration has a valid one, and the offending key or value.

#### Scenario: An option the type does not take
- **WHEN** a field-declaration run adds `pattern = "x"` to the declaration of `stock`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:`, `stock` and `pattern`

#### Scenario: An unknown option
- **WHEN** a field-declaration run adds `tabs = true` to the declaration of `chemical_class`
- **THEN** it exits 2, stdout is empty, and stderr contains `chemical_class` and `tabs`

#### Scenario: A facet or a search where the type does not take it
- **WHEN** a field-declaration run adds `facet = true` to the declaration of `short_name`; and, separately, adds `search = true` to the declaration of `stock`
- **THEN** each exits 2, and stderr contains `short_name` and `facet`, and `stock` and `search`, respectively

#### Scenario: A key the catalogue reserves
- **WHEN** a field-declaration run adds a declaration with `key = "title"`, `type = "text"` and `label = "Title"`
- **THEN** it exits 2, and stderr contains `title`

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

### Requirement: Field data for the site
`pipeline.fields_data(settings, language)` SHALL return the field data that the build stages as `build/data/fields.json` (build-script "build subcommand"), given the path of the collection's settings file and the site's language. The data is a table whose only key is `compound`, holding one table per declaration of `fields.compound`, in declared order, each with these keys and no other:
- `key`, `type` and `column`, as declared, `column` with its default;
- `facet`: only for a `boolean` or `choice` field, as declared, with its default;
- `search`: only for a `text` field, as declared, with its default;
- `label`: the field's shown label, its `label_de` on a German site when it declares one, and its `label` otherwise;
- `unit`: only for a `number` field that declares one, as declared;
- `multiple`: only for a `choice` field, as declared, with its default;
- `values`: only for a `choice` field, a table holding every value of its vocabulary under the value's key, each a table of `label`, the value's shown label, chosen as the field's is; `path`, the shown labels of the value's ancestors, outermost first, followed by its own; and `ancestors`, the keys of its ancestors, outermost first;
- `order`: only for a `choice` field, the keys of every value of its vocabulary, each top-level value in file order followed by the values filed under it, in the same order, recursively.

A settings file that does not exist, or that declares no field, gives `{"compound": []}`. A settings file that breaks a rule of the requirements "Field declarations" or "Vocabularies" raises `validate.ConfigError`.

#### Scenario: Field data in both languages
- **WHEN** a test calls `fields_data` on `tests/fixtures/fields/orgsyndb.toml` with the language `en`, and again with `de`
- **THEN** each lists the six fixture fields in declared order with the stated keys, `stock` has the `unit` `g`, `chemical_class` has `multiple` `true` and `column` `true`, and `storage` has `multiple` `false`
- **AND** in `en` the value `ketones` of `chemical_class` has the label `Ketones` and the path `["Carbonyl compounds", "Ketones"]`, and in `de` the label `Ketone` and the path `["Carbonylverbindungen", "Ketone"]`
- **AND** `short_name`, which declares no `label_de`, has the label `Short name` in both
- **AND** `item_number` and `short_name` have `search` `false`, `in_house`, `chemical_class` and `storage` have `facet` `false`, the value `ketones` has the `ancestors` `["carbonyl-compounds"]` and `alcohols` none, and the `order` of `chemical_class` is `["carbonyl-compounds", "ketones", "esters", "alcohols"]`

#### Scenario: Depth-first order
- **WHEN** a test calls `fields_data` on a copy of the fixture settings whose `vocabularies/chemical-classes.toml` lists, in this order, `esters` under `carbonyl-compounds`, `alcohols`, `carbonyl-compounds`, `ketones` under `carbonyl-compounds`, and `aryl-ketones` under `ketones`
- **THEN** the `order` of `chemical_class` is `["alcohols", "carbonyl-compounds", "esters", "ketones", "aryl-ketones"]`, and `aryl-ketones` has the `ancestors` `["carbonyl-compounds", "ketones"]`

#### Scenario: No settings file
- **WHEN** a test calls `fields_data` on a path that does not exist
- **THEN** it returns `{"compound": []}`

