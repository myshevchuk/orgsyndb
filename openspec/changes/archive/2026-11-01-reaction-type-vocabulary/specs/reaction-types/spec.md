## ADDED Requirements

### Requirement: Reaction-type vocabulary
A collection's reaction types SHALL be the values of its vocabulary `reaction-types`, the file `vocabularies/reaction-types.toml` in the directory of its `orgsyndb.toml`. The file follows the rules of compound-fields "Vocabularies", except that no value takes `parent`: the reaction types form a single level. A collection without the file has no reaction type, so the reaction type of each of its procedures is unknown (procedure-schema "Controlled reaction type").

The validator reads the file whether or not a declaration names it, from the directory of the settings file it reads (procedure-validation "Command-line interface"). A file that exists and breaks a rule is a configuration error (procedure-validation "Vocabulary file errors are configuration errors"). A declared `choice` field may name the vocabulary `reaction-types` like any other; it then needs the file, and the file's absence is the configuration error compound-fields "Declaration errors are configuration errors" states for a missing vocabulary.

#### Scenario: The working directory's reaction types
- **WHEN** a test runs `<app>/tools/validate.py` without `--settings`, with `cwd` set to a temporary directory holding `vocabularies/reaction-types.toml` whose only value is `reductive-amination` (`label = "Reductive amination"`), with `--compounds <app>/tests/fixtures/compounds` and `--static-dir <app>/tests/fixtures/static`, on a content root holding the baseline with `reaction_types = ["reductive-amination"]`, and again on one holding the baseline unchanged
- **THEN** the first exits 0 and prints nothing to stdout
- **AND** the second reports exactly one error, field `reaction_types`, containing `unknown reaction type "esterification"` and `vocabularies/reaction-types.toml`

#### Scenario: A collection without reaction types
- **WHEN** a settings variant run on `baseline` deletes `vocabularies/reaction-types.toml`
- **THEN** it reports exactly one error, field `reaction_types`, containing `unknown reaction type "esterification"` and `vocabularies/reaction-types.toml`

#### Scenario: A declared field names the reaction types
- **WHEN** a procedure-field run (procedure-fields "Procedure field fixture") appends to `orgsyndb.toml` the declaration of `fields.procedure` `side_reaction` (`choice`, labelled `Side reaction`, `vocabulary = "reaction-types"`) and sets `side_reaction = "reduction"` in `OSDB-0100-baseline.md`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: A declared field needs the file
- **WHEN** a procedure-field run appends the same declaration of `side_reaction` to `orgsyndb.toml` and deletes `vocabularies/reaction-types.toml`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:`, `side_reaction` and `reaction-types.toml`

#### Scenario: Nested reaction types are refused
- **WHEN** a settings variant run on `baseline` adds `parent = "esterification"` to the value `reduction` of `vocabularies/reaction-types.toml`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:`, `reaction-types.toml`, `reduction` and `parent`

#### Scenario: An entry key outside the vocabulary format
- **WHEN** a settings variant run on `baseline` adds `note = "x"` to the value `reduction` of `vocabularies/reaction-types.toml`
- **THEN** it exits 2, stdout is empty, and stderr contains `reaction-types.toml`, `reduction` and `note`

### Requirement: Starter reaction types
The application SHALL ship `templates/reaction-types.toml`, a reaction-type vocabulary that starts with comment lines saying that it lists the collection's reaction types and that the collection may change it. Its values include at least `acylation`, `aldol-condensation`, `cross-coupling`, `esterification`, `olefination`, `protection`, `reduction` and `reductive-amination`, and every value has a `label_de`. `init` copies it into a new collection (collection "init subcommand"), and the demo collection holds it (sample-procedures "Demo collection").

#### Scenario: The starter vocabulary is well formed and complete
- **WHEN** a test loads `templates/reaction-types.toml` with `tomllib`
- **THEN** every top-level key matches `^[a-z0-9]+(-[a-z0-9]+)*$` and maps to a table whose keys are exactly `label` and `label_de`, both non-empty strings
- **AND** the keys include `acylation`, `aldol-condensation`, `cross-coupling`, `esterification`, `olefination`, `protection`, `reduction` and `reductive-amination`
- **AND** the file's first line is a comment

#### Scenario: The validator accepts the starter vocabulary
- **WHEN** a settings variant run on an empty temporary content root replaces `vocabularies/reaction-types.toml` with a copy of `templates/reaction-types.toml`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Reaction-type data for the site
`pipeline.reaction_types_data(settings, language)` SHALL return the reaction-type data that the build stages as `build/data/reaction_types.json` (build-script "build subcommand"), given the path of the collection's settings file and the site's language. The data is a table with one key per value of `vocabularies/reaction-types.toml` in the directory of the settings file, each mapped to a table holding only `label`: the value's `label_de` when the language is `de` and the value has one, its `label` otherwise. A file that does not exist gives an empty table. It raises `validate.ConfigError` when the file breaks a rule of the requirement "Reaction-type vocabulary".

The site reads the data as `site.Data.collection.reaction_types` (site-build "Hugo configuration"). Wherever it shows a reaction type's vocabulary label (site-theme, site-catalogue, synthesis-sequences), the label is the data's `label` for that reaction type.

#### Scenario: Labels in either language
- **WHEN** a test calls `reaction_types_data` on the test collection's `orgsyndb.toml` with the language `en`, and again with `de`
- **THEN** both results have exactly the keys of the test collection's `vocabularies/reaction-types.toml`, each mapped to a table whose only key is `label`
- **AND** `aldol-condensation` has the label `Aldol condensation` in `en` and `Aldolkondensation` in `de`

#### Scenario: A value without a German label
- **WHEN** a test calls `reaction_types_data` with the language `de` on a copy of the test collection's `orgsyndb.toml` and `vocabularies/` from whose `reaction-types.toml` the `label_de` of `esterification` is removed
- **THEN** `esterification` has the label `Esterification`

#### Scenario: No reaction types
- **WHEN** a test calls `reaction_types_data` on a settings file in a temporary directory without `vocabularies/`
- **THEN** it returns an empty table

#### Scenario: A broken vocabulary
- **WHEN** a test calls `reaction_types_data` on a copy of the test collection's `orgsyndb.toml` and `vocabularies/` whose `reaction-types.toml` gives `reduction` the line `parent = "oxidation"`
- **THEN** it raises `validate.ConfigError`

#### Scenario: The site takes its labels from the collection
- **WHEN** a test builds a copy of the test collection in locale `en` after changing the `label` of `esterification` in its `vocabularies/reaction-types.toml` to `Ester formation`
- **THEN** the build exits 0, the `h1` of `public/reaction_types/esterification/index.html` is `Ester formation`, and the `/reaction_types/` list links that page with the text `Ester formation`
- **AND** the metadata panel and the procedure table row of every published procedure whose reaction type is `esterification` show `Ester formation`
