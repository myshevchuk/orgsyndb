# procedure-fields Specification

## Purpose
Define the fields a collection declares for its procedures in its settings file: the declarations and their configuration errors, the checks of procedure values, how Org sources set them, the field data the build stages for the site, and the validator fixture that proves them.
## Requirements
### Requirement: Procedure field declarations
A collection SHALL declare the fields its procedures carry beyond the procedure schema in its `orgsyndb.toml`, as the array of tables `fields.procedure`, one table per field, in the order the site shows them. `fields`, when present, is a table whose only key is `procedure`; a collection whose `orgsyndb.toml` has no `fields`, or whose `fields` holds no `procedure`, declares no procedure field. Each declaration holds:
- `key`: required. It matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, does not end in `_de`, no other declaration has it, and it is none of these reserved keys:
  - the keys of the procedure schema: `id`, `slug`, `title`, `date`, `lastmod`, `authors`, `status`, `reaction_types`, `tags`, `products`, `scale`, `hazards`, `substrates`, `scope`, `scheme_image`, `checked_by`, `references`, `ai_model`, `language`, `draft`, `description`, `aliases`, `weight`, `author` and `url`;
  - the other front-matter keys Hugo reads for itself, written in lower case: `build`, `cascade`, `expirydate`, `headless`, `iscjklanguage`, `keywords`, `kind`, `lang`, `layout`, `linktitle`, `markup`, `menu`, `menus`, `modified`, `outputs`, `params`, `path`, `pubdate`, `publishdate`, `published`, `resources`, `sitemap`, `sites`, `summary`, `translationkey`, `type` and `unpublishdate`, and the weight Hugo reads for each taxonomy, `authors_weight`, `reaction_types_weight` and `tags_weight`;
  - the record keys and address parameters of the procedure catalogue that these lists do not already name: `tag`, `created`, `text`, `q`, `sort` and `view`;
  - the keys of the journal fields, `notebook` and `project` (Journal fields).
  A procedure sets the field under this key.
- `type`: required; `text`, `number`, `boolean` or `choice`.
- `label`: required non-empty string, the field's name on an English site. `label_de`: optional non-empty string, its name on a German site, which shows `label` when it is absent.
- `required`: optional boolean, default `false`. When `true`, every procedure sets the field.
- For `text`: `pattern`, an optional string holding a Python regular expression that the whole value matches; and `unique`, an optional boolean, default `false`, under which no two procedures set the same value.
- For `number`: `min` and `max`, optional finite numbers (TOML integer or float, never boolean) bounding the value inclusively, `min` not greater than `max`; `unit`, an optional non-empty string written after the value; and `unique` as for `text`.
- For `boolean`: `facet`, an optional boolean, default `false`, under which the procedure catalogues offer the field as a filter (site-catalogue "Catalogue controls").
- For `choice`: `vocabulary`, required, the name of one of the registry's vocabularies, `chemical-classes`, `inventory-groups`, `projects` or `reaction-types` (lab-registry "Snapshot"); `multiple`, an optional boolean, default `false`, under which a procedure sets a list of terms rather than one; and `facet` as for `boolean`.

A declaration holds no other key, and no key that its type does not take. The terms of a vocabulary are those of the collection's registry (compound-registry "Reading the registry"); a term's ancestors are the terms its `parent` leads to, outermost first.

#### Scenario: The fixture declarations are accepted
- **WHEN** a procedure-field run makes no change
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Facets on a boolean and a choice field
- **WHEN** a procedure-field run adds `facet = true` to the declarations of `inert_atmosphere` and `funding`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Procedure declaration errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr when the settings file it reads (procedure-validation "Command-line interface") was named by `--settings` and does not exist, cannot be read as UTF-8 TOML, breaks the rules of collection "Collection layout" for `format` and the top-level keys, or breaks a rule of the requirement "Procedure field declarations". In particular this holds when:
- `fields` is not a table or holds a key other than `procedure`, `compound` among them, or `fields.procedure` is not an array of tables;
- a declaration lacks `key`, `type` or `label`, has a value of the wrong type, or holds a key that is unknown, that its type does not take, or that is `column`, `search`, `tabs` or `beside`;
- a `key` breaks its pattern, ends in `_de`, is reserved or is declared twice;
- a `pattern` is not a valid Python regular expression, `min` or `max` is not finite, or `min` is greater than `max`;
- the vocabulary a `choice` field names is not one of the registry's four.

The message names the settings file, the field's key when the declaration has a valid one, and the offending key or value; a message about a declaration's `key` also names `fields.procedure`, and one about another entity under `fields` names it, such as `fields.compound`.

#### Scenario: Options a procedure field does not take
- **WHEN** a procedure-field run adds `column = true` to the declaration of `sample_code`; separately, adds `search = true` to the declaration of `sample_code`; separately, adds `tabs = true` to the declaration of `funding`; and separately, adds `beside = true` to the declaration of `working_time`
- **THEN** each exits 2, stdout is empty, and stderr contains `validate.py: error:` and, respectively, `sample_code` and `column`, `sample_code` and `search`, `funding` and `tabs`, and `working_time` and `beside`

#### Scenario: Reserved keys
- **WHEN** a procedure-field run adds a declaration with `type = "text"`, `label = "X"` and, in three separate runs, `key = "status"`, `key = "layout"` and `key = "tag"`
- **THEN** each exits 2, and stderr contains `fields.procedure` and, respectively, `status`, `layout` and `tag`

#### Scenario: A key declared twice
- **WHEN** a procedure-field run adds a second declaration with `key = "sample_code"`, `type = "text"` and `label = "Sample code"`
- **THEN** it exits 2, and stderr contains `sample_code` and `fields.procedure`

#### Scenario: A single table instead of an array
- **WHEN** a test runs the validator with `--settings` naming a settings file that holds `format = 1` and one `[fields.procedure]` table with `key`, `type` and `label`
- **THEN** it exits 2, and stderr contains `fields.procedure`

#### Scenario: A missing vocabulary
- **WHEN** a procedure-field run sets `vocabulary = "no-such-vocabulary"` in the declaration of `funding`
- **THEN** it exits 2, and stderr contains `no-such-vocabulary`

#### Scenario: A compound declaration
- **WHEN** a procedure-field run adds to its `orgsyndb.toml` a `[[fields.compound]]` declaration with `key = "sample_code"`, `type = "text"` and `label = "Sample code"`
- **THEN** it exits 2, and stderr contains `fields.compound`

#### Scenario: A misspelt top-level key
- **WHEN** a procedure-field run replaces every `[[fields.procedure]]` of its `orgsyndb.toml` with `[[feilds.procedure]]`
- **THEN** it exits 2, and stderr contains `feilds`

#### Scenario: A bound that is not a number
- **WHEN** a procedure-field run adds `max = nan` to the declaration of `working_time`
- **THEN** it exits 2, and stderr contains `working_time` and `max`

#### Scenario: A named settings file that does not exist
- **WHEN** a fixture run on `baseline` adds `--settings tests/fixtures/no-such-settings.toml`
- **THEN** it exits 2, stdout is empty, and stderr contains `no-such-settings.toml`

### Requirement: Procedure field values
For each procedure field its collection declares, the validator SHALL check the value that each procedure sets under the field's key, a Markdown source or an Org export alike, and report each problem on the procedure file's path under that key:
- `text`: a non-empty string (`must be a string`, `must not be empty`) that, when the field declares `pattern`, matches it as a whole (`must match the pattern <pattern>`).
- `number`: a finite TOML integer or float, never a boolean (`must be a number, unquoted`), not less than `min` (`must be at least <min>`) and not greater than `max` (`must be at most <max>`).
- `boolean`: `true` or `false` (`must be true or false, unquoted`).
- `choice`: a string (`must be a string`) that is a term of the field's vocabulary (`unknown value "<v>" of the vocabulary <name>`). Under `multiple`, a non-empty list of strings (`must be a list of strings, e.g. ["<a term>"]`, `must not be empty`), each a term of the vocabulary, with one `unknown value` error per string that is not, and none repeated (`repeats "<v>"`).

A value of the wrong type draws that one error and no other. A choice may name any term of its vocabulary, a top-level term or one filed under another. A procedure that does not set a field declared `required` gets an error containing `required field missing`; this holds for a general procedure as for any other. Under `unique`, the procedures compared are those that stand for their IDs, one file per ID, the reference variant of localization "Procedure variants" where an ID has several files: every value that passes the checks of its field and is set by more than one of them draws an error on each of those files, containing `also set by` and the IDs of the other procedures. A file whose front matter does not parse sets no value. A key of a declared procedure field is no key outside the schema (procedure-schema "Keys outside the schema").

#### Scenario: Declared values pass
- **WHEN** a procedure-field run sets `sample_code = "AE-1/2"`, `working_time = 2.5`, `inert_atmosphere = false` and `funding = "first-year-practical"` in `OSDB-0100-baseline.md`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: A text value that breaks its pattern
- **WHEN** a procedure-field run sets `sample_code = "AE-12"` in `OSDB-0100-baseline.md`
- **THEN** it reports exactly one error, on the path ending `OSDB-0100-baseline.md`, field `sample_code`, containing `must match the pattern`

#### Scenario: A quoted number
- **WHEN** a procedure-field run sets `working_time = "2"` in `OSDB-0100-baseline.md`
- **THEN** it reports exactly one error, field `working_time`, containing `must be a number`

#### Scenario: A value outside the vocabulary
- **WHEN** a procedure-field run sets `funding = "outreach"` in `OSDB-0100-baseline.md`
- **THEN** it reports exactly one error, field `funding`, containing `unknown value "outreach"` and `projects`

#### Scenario: A required field on every procedure
- **WHEN** a procedure-field run adds `required = true` to the declaration of `funding` and copies `tests/fixtures/general/OSDB-0140-general.md` into the content root
- **THEN** it exits 1 and reports exactly two problems, both errors with field `funding` containing `required field missing`, one on each procedure file

#### Scenario: A value set by two procedures
- **WHEN** a procedure-field run sets `sample_code = "AE-1/2"` in `OSDB-0100-baseline.md` and adds `OSDB-0101-copy.md`, a copy of it whose `id` is `OSDB-0101` and `slug` `osdb-0101`
- **THEN** it exits 1 and reports exactly two problems, both errors with field `sample_code` containing `also set by`, the one on `OSDB-0100-baseline.md` naming `OSDB-0101` and the other naming `OSDB-0100`

#### Scenario: Variants of one procedure are one holder
- **WHEN** a procedure-field run sets `sample_code = "AE-1/2"` in `OSDB-0100-baseline.md` and adds `OSDB-0100-baseline.de.md`, a copy of it whose eight section headings are the German ones
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Declared fields in Org sources
The export SHALL write a declared procedure field that an Org procedure source sets on a `#+HUGO_CUSTOM_FRONT_MATTER:` line into the exported front matter under its key, typed as the pinned ox-hugo and tomelr type custom front matter: a double-quoted string as a TOML string, an unquoted number as a TOML number, `true` and `false` as TOML booleans, and a quoted list of strings, `'("a" "b")`, as a TOML array of strings. tomelr writes a string without quotes, whether the source quoted it or not and wherever it stands, list entries included, when it reads `true` or `false`, has the form of an RFC 3339 date or date-time (`2026-01-01`, `2026-01-01T10:00:00+01:00`), or is an optional sign followed by digits and underscores that Emacs reads as a fixnum (`1234`, `-7`, `7_000`, `0012`). Such a string cannot reach the export as a string: a text value, a choice value or an entry of a multiple choice's list of this form from an Org source makes the validator report the value's type, or, where the unquoted form is not valid TOML, as with a leading zero, makes the export's front matter fail to parse.

#### Scenario: Org values reach the export with their types
- **WHEN** an integration test exports a copy of the demo collection with `tools/orgsyndb -C <collection> export`
- **THEN** it exits 0, and the export of every Org sample sets each journal field (Journal fields) and declared procedure field that its file of the same stem in `tests/fixtures/collection/md/procedures/` sets, with an equal value of the same TOML type, and no other

#### Scenario: A quoted integer is no text
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on a copy of the demo collection whose registry, a copy of the demo registry named by `ORGSYNDB_REGISTRY`, gains the top-level project `2027` (`label` `2027`), and whose `org/procedures/OSDB-0001-salicylic-acid.org` and `org/procedures/OSDB-0001-salicylic-acid.de.org` set the `notebook` value `"1234"` and the `project` value `"2027"` in place of their own
- **THEN** it exits 1, `build/export/OSDB-0001-salicylic-acid.md` sets `notebook = 1234` and `project = 2027`, and stdout has error lines on that export with the field `notebook` and with the field `project`, each containing `must be a string`

### Requirement: Procedure field data
`pipeline.fields_data(settings, registry, language)` SHALL give under the key `procedure` one table per journal field (Journal fields), in their order, and then one per declaration of `fields.procedure`, in declared order, each with these keys and no other:
- `key` and `type`, as declared;
- `label`: the field's shown label, its `label_de` on a German site when it declares one, and its `label` otherwise;
- `facet`: only for a `boolean` or `choice` field, as declared, with its default;
- `unit`: only for a `number` field that declares one, as declared;
- `multiple`, as declared with its default, and `values` and `order`: only for a `choice` field, `values` and `order` as compound-fields "Field data for the site" defines them for a registry field of its vocabulary.

A settings file that does not exist, or that declares no procedure field, gives `procedure` the journal fields alone.

#### Scenario: Procedure field data in both languages
- **WHEN** a test calls `fields_data` on `tests/fixtures/procedure-fields/orgsyndb.toml` and the fixture registry with the language `en`, and again with `de`
- **THEN** each gives `compound` the four registry fields and lists under `procedure` the two journal fields and then the four fixture fields in declared order with the stated keys and no `column`, `search` or `tabs`; `working_time` has the `unit` `h`, `funding` has `multiple` `false` and `facet` `false`, the journal field `project` has `facet` `true`, and `inert_atmosphere` has `facet` `false`
- **AND** in `en` the value `first-year-practical` of `funding` has the label `First-year practical`, the path `["Teaching", "First-year practical"]` and the `ancestors` `["teaching"]`, and in `de` the label `Grundpraktikum` and the path `["Lehre", "Grundpraktikum"]`; `inert_atmosphere`, which declares no `label_de`, has the label `Inert atmosphere` in both; and the `order` of `funding` is `["research", "teaching", "first-year-practical"]`

### Requirement: Procedure field fixture
The repository SHALL ship the validator fixture `tests/fixtures/procedure-fields/`: a settings file `orgsyndb.toml` holding `format = 1` and, in this order, the declarations of `fields.procedure` `sample_code` (`text`, labelled `Sample code` and `Probencode`, `pattern = '[A-Z]{2}-\d+/\d+'`, `unique`), `working_time` (`number`, labelled `Working time` and `Arbeitszeit`, `unit = "h"`, `min = 0`), `inert_atmosphere` (`boolean`, labelled `Inert atmosphere`, with no `label_de`) and `funding` (`choice`, labelled `Funding` and `Förderung`, `vocabulary = "projects"`), none of them `required` or a `facet`, and no other file. Its projects are those of the fixture registry (procedure-validation "Fixture suite"): `teaching` (`Teaching`, `Lehre`), `first-year-practical` (`First-year practical`, `Grundpraktikum`), filed under `teaching`, and `research` (`Research`, `Forschung`).

A procedure-field run copies `tests/fixtures/procedure-fields/` and the fixture registry to a fresh temporary directory, writes `tests/fixtures/baseline/OSDB-0100-baseline.md` as the only file of a fresh content root there, applies the stated change (a procedure file named alone is one of that content root, `orgsyndb.toml` that of the procedure-fields copy), and runs `tools/validate.py --static-dir tests/fixtures/static` with `--registry` naming the registry copy, `--settings` naming the copy of `orgsyndb.toml`, and the content root. "Reports exactly one" counts the stdout lines of the whole run, as for a registry variant run (procedure-validation "Fixture suite").

#### Scenario: The fixture matches its description
- **WHEN** a test reads `tests/fixtures/procedure-fields/` and the projects of the fixture registry
- **THEN** the declarations and the projects are exactly those stated, and the directory holds no other file

### Requirement: Journal fields
The tools SHALL give every procedure two built-in fields, the journal fields, which they treat as declared procedure fields wherever they treat those, placed before the collection's declarations, in this order:

| key | type and options | label (English, German) |
|---|---|---|
| `notebook` | `text`, `pattern = '[A-Z0-9]+(-[A-Z0-9]+)*/[1-9][0-9]{0,3}'`, `unique` | `Lab notebook`, `Laborjournal` |
| `project` | `choice`, vocabulary `projects`, `facet` | `Project`, `Projekt` |

A procedure may set either, and neither is required. `notebook` names the journal entry the procedure was written from (lab-journal "Notebooks and entries"), as `<code>/<number>`; besides the checks of a `text` field, a value whose code, the part before `/`, is not the `code` of one of the registry's `notebooks` (lab-registry "Snapshot") is an error under `notebook`: `unknown notebook "<code>"; the registry has no notebook of this code`. `project` names a term of the registry's projects.

#### Scenario: A registered notebook
- **WHEN** a test validates the test collection with `OSDB-0002-aspirin.md` setting `notebook = "AE-1/14"`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: An unknown notebook
- **WHEN** a test validates the test collection with `OSDB-0002-aspirin.md` setting `notebook = "ZZ-9/1"`
- **THEN** it reports exactly one error, field `notebook`, containing `unknown notebook "ZZ-9"`

#### Scenario: A journal field declared
- **WHEN** a procedure-field run adds a declaration with `key = "project"`, `type = "text"` and `label = "Project"`
- **THEN** it exits 2, and stderr contains `fields.procedure` and `project`

