# procedure-fields Specification

## Purpose
Define the fields a collection declares for its procedures in its settings file: the declarations and their configuration errors, the checks of procedure values, how Org sources set them, the field data the build stages for the site, and the validator fixture that proves them.
## Requirements
### Requirement: Procedure field declarations
A collection SHALL declare the fields its procedures carry beyond the procedure schema in its `orgsyndb.toml`, as the array of tables `fields.procedure`, one table per field, in the order the site shows them. A collection whose `fields` holds no `procedure` declares no procedure field. A declaration holds the keys of a compound field declaration (compound-fields "Field declarations"), with the same meanings, defaults, types and vocabularies, except:
- it takes neither `column`, nor `search`, nor `tabs`, nor `beside`;
- for a `boolean` or `choice` field, `facet = true` makes the field a filter of the procedure catalogues (site-catalogue "Catalogue controls");
- `required` and `unique` concern procedures, not compounds: under `required` every procedure sets the field, and under `unique` no two procedures set the same value;
- its `key` matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, does not end in `_de`, no other declaration of `fields.procedure` has it, and it is none of these reserved keys:
  - the keys of the procedure schema: `id`, `slug`, `title`, `date`, `lastmod`, `authors`, `status`, `reaction_types`, `tags`, `products`, `scale`, `hazards`, `substrates`, `scope`, `scheme_image`, `checked_by`, `references`, `ai_model`, `language`, `draft`, `description`, `aliases`, `weight`, `author` and `url`;
  - the other front-matter keys Hugo reads for itself, written in lower case: `build`, `cascade`, `expirydate`, `headless`, `iscjklanguage`, `keywords`, `kind`, `lang`, `layout`, `linktitle`, `markup`, `menu`, `menus`, `modified`, `outputs`, `params`, `path`, `pubdate`, `publishdate`, `published`, `resources`, `sitemap`, `sites`, `summary`, `translationkey`, `type` and `unpublishdate`, and the weight Hugo reads for each taxonomy, `authors_weight`, `reaction_types_weight` and `tags_weight`;
  - the record keys and address parameters of the procedure catalogue that these lists do not already name: `tag`, `created`, `text`, `q`, `sort` and `view`.

A procedure field and a compound field may have the same key. The vocabularies a procedure field names are those of compound-fields "Vocabularies", shared with the compound fields.

#### Scenario: The fixture declarations are accepted
- **WHEN** a procedure-field run makes no change
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Facets on a boolean and a choice field
- **WHEN** a procedure-field run adds `facet = true` to the declarations of `inert_atmosphere` and `project`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: One key for a compound and a procedure field
- **WHEN** a procedure-field run adds to its `orgsyndb.toml` a `[[fields.compound]]` declaration with `key = "notebook"`, `type = "text"` and `label = "Notebook"`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Procedure declaration errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr when its settings file breaks a rule of the requirement "Procedure field declarations", as compound-fields "Declaration errors are configuration errors" states for the compound declarations. In particular this holds when `fields.procedure` is not an array of tables; when a declaration lacks `key`, `type` or `label`, has a value of the wrong type, or holds a key that is unknown, that its type does not take, or that is `column`, `search`, `tabs` or `beside`; when a `key` breaks its pattern, ends in `_de`, is reserved or is declared twice in `fields.procedure`; and when a `pattern`, a bound or a vocabulary breaks the rules of the compound declarations. The message names the settings file or the vocabulary file, the field's key when the declaration has a valid one, and the offending key or value; a message about a declaration's `key` also names `fields.procedure`.

#### Scenario: Options a procedure field does not take
- **WHEN** a procedure-field run adds `column = true` to the declaration of `notebook`; separately, adds `search = true` to the declaration of `notebook`; separately, adds `tabs = true` to the declaration of `project`; and separately, adds `beside = true` to the declaration of `working_time`
- **THEN** each exits 2, stdout is empty, and stderr contains `validate.py: error:` and, respectively, `notebook` and `column`, `notebook` and `search`, `project` and `tabs`, and `working_time` and `beside`

#### Scenario: Reserved keys
- **WHEN** a procedure-field run adds a declaration with `type = "text"`, `label = "X"` and, in three separate runs, `key = "status"`, `key = "layout"` and `key = "tag"`
- **THEN** each exits 2, and stderr contains `fields.procedure` and, respectively, `status`, `layout` and `tag`

#### Scenario: A key declared twice
- **WHEN** a procedure-field run adds a second declaration with `key = "notebook"`, `type = "text"` and `label = "Notebook"`
- **THEN** it exits 2, and stderr contains `notebook` and `fields.procedure`

#### Scenario: A single table instead of an array
- **WHEN** a test runs the validator with `--settings` naming a settings file that holds `format = 1` and one `[fields.procedure]` table with `key`, `type` and `label`
- **THEN** it exits 2, and stderr contains `fields.procedure`

#### Scenario: A missing vocabulary
- **WHEN** a procedure-field run sets `vocabulary = "no-such-vocabulary"` in the declaration of `project`
- **THEN** it exits 2, and stderr contains `no-such-vocabulary`

### Requirement: Procedure field values
For each procedure field its collection declares, the validator SHALL check the value that each procedure sets under the field's key, a Markdown source or an Org export alike, by the rules of compound-fields "Field values" with their messages, and report each problem on the procedure file's path under that key. A procedure that does not set a field declared `required` gets an error containing `required field missing`; this holds for a general procedure as for any other. Under `unique`, the procedures compared are those that stand for their IDs, one file per ID, the reference variant of localization "Procedure variants" where an ID has several files: every value that passes the checks of its field and is set by more than one of them draws an error on each of those files, containing `also set by` and the IDs of the other procedures. A file whose front matter does not parse sets no value. A key of a declared procedure field is no key outside the schema (procedure-schema "Keys outside the schema").

#### Scenario: Declared values pass
- **WHEN** a procedure-field run sets `notebook = "AE-1/2"`, `working_time = 2.5`, `inert_atmosphere = false` and `project = "first-year-practical"` in `OSDB-0100-baseline.md`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: A text value that breaks its pattern
- **WHEN** a procedure-field run sets `notebook = "AE-12"` in `OSDB-0100-baseline.md`
- **THEN** it reports exactly one error, on the path ending `OSDB-0100-baseline.md`, field `notebook`, containing `must match the pattern`

#### Scenario: A quoted number
- **WHEN** a procedure-field run sets `working_time = "2"` in `OSDB-0100-baseline.md`
- **THEN** it reports exactly one error, field `working_time`, containing `must be a number`

#### Scenario: A value outside the vocabulary
- **WHEN** a procedure-field run sets `project = "outreach"` in `OSDB-0100-baseline.md`
- **THEN** it reports exactly one error, field `project`, containing `unknown value "outreach"` and `vocabularies/projects.toml`

#### Scenario: A required field on every procedure
- **WHEN** a procedure-field run adds `required = true` to the declaration of `project` and copies `tests/fixtures/general/OSDB-0140-general.md` into the content root
- **THEN** it exits 1 and reports exactly two problems, both errors with field `project` containing `required field missing`, one on each procedure file

#### Scenario: A value set by two procedures
- **WHEN** a procedure-field run sets `notebook = "AE-1/2"` in `OSDB-0100-baseline.md` and adds `OSDB-0101-copy.md`, a copy of it whose `id` is `OSDB-0101` and `slug` `osdb-0101`
- **THEN** it exits 1 and reports exactly two problems, both errors with field `notebook` containing `also set by`, the one on `OSDB-0100-baseline.md` naming `OSDB-0101` and the other naming `OSDB-0100`

#### Scenario: Variants of one procedure are one holder
- **WHEN** a procedure-field run sets `notebook = "AE-1/2"` in `OSDB-0100-baseline.md` and adds `OSDB-0100-baseline.de.md`, a copy of it whose eight section headings are the German ones
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Declared fields in Org sources
The export SHALL write a declared procedure field that an Org procedure source sets on a `#+HUGO_CUSTOM_FRONT_MATTER:` line into the exported front matter under its key, typed as the pinned ox-hugo and tomelr type custom front matter: a double-quoted string as a TOML string, an unquoted number as a TOML number, `true` and `false` as TOML booleans, and a quoted list of strings, `'("a" "b")`, as a TOML array of strings. tomelr writes a string without quotes, whether the source quoted it or not and wherever it stands, list entries included, when it reads `true` or `false`, has the form of an RFC 3339 date or date-time (`2026-01-01`, `2026-01-01T10:00:00+01:00`), or is an optional sign followed by digits and underscores that Emacs reads as a fixnum (`1234`, `-7`, `7_000`, `0012`). Such a string cannot reach the export as a string: a text value, a choice value or an entry of a multiple choice's list of this form from an Org source makes the validator report the value's type, or, where the unquoted form is not valid TOML, as with a leading zero, makes the export's front matter fail to parse.

#### Scenario: Org values reach the export with their types
- **WHEN** an integration test exports a copy of the demo collection with `tools/orgsyndb -C <collection> export`
- **THEN** it exits 0, and the export of every Org sample sets each declared procedure field that its file of the same stem in `tests/fixtures/collection/md/procedures/` sets, with an equal value of the same TOML type, and no other

#### Scenario: A quoted integer is no text
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on a copy of the demo collection whose `vocabularies/projects.toml` gains the top-level value `2027` (`label = "2027"`), and whose `org/procedures/OSDB-0001-salicylic-acid.org` and `org/procedures/OSDB-0001-salicylic-acid.de.org` set the `notebook` value `"1234"` and the `project` value `"2027"` in place of their own
- **THEN** it exits 1, `build/export/OSDB-0001-salicylic-acid.md` sets `notebook = 1234` and `project = 2027`, and stdout has error lines on that export with the field `notebook` and with the field `project`, each containing `must be a string`

### Requirement: Procedure field data
`pipeline.fields_data(settings, language)` SHALL give under the key `procedure` one table per declaration of `fields.procedure`, in declared order, each with these keys and no other:
- `key` and `type`, as declared;
- `label`: the field's shown label, chosen as for a compound field;
- `facet`: only for a `boolean` or `choice` field, as declared, with its default;
- `unit`: only for a `number` field that declares one, as declared;
- `multiple`, `values` and `order`: only for a `choice` field, as compound-fields "Field data for the site" defines them for a compound field.

A settings file that does not exist, or that declares no procedure field, gives `procedure` an empty list.

#### Scenario: Procedure field data in both languages
- **WHEN** a test calls `fields_data` on `tests/fixtures/procedure-fields/orgsyndb.toml` with the language `en`, and again with `de`
- **THEN** each gives `compound` an empty list and lists under `procedure` the four fixture fields in declared order with the stated keys and no `column`, `search` or `tabs`; `working_time` has the `unit` `h`, `project` has `multiple` `false` and `facet` `false`, and `inert_atmosphere` has `facet` `false`
- **AND** in `en` the value `first-year-practical` of `project` has the label `First-year practical`, the path `["Teaching", "First-year practical"]` and the `ancestors` `["teaching"]`, and in `de` the label `Grundpraktikum` and the path `["Lehre", "Grundpraktikum"]`; `inert_atmosphere`, which declares no `label_de`, has the label `Inert atmosphere` in both; and the `order` of `project` is `["teaching", "first-year-practical", "research"]`

### Requirement: Procedure field fixture
The repository SHALL ship the validator fixture `tests/fixtures/procedure-fields/`: a settings file `orgsyndb.toml` holding `format = 1` and, in this order, the declarations of `fields.procedure` `notebook` (`text`, labelled `Lab notebook` and `Laborjournal`, `pattern = '[A-Z]{2}-\d+/\d+'`, `unique`), `working_time` (`number`, labelled `Working time` and `Arbeitszeit`, `unit = "h"`, `min = 0`), `inert_atmosphere` (`boolean`, labelled `Inert atmosphere`, with no `label_de`) and `project` (`choice`, labelled `Project` and `Projekt`, `vocabulary = "projects"`), none of them `required` or a `facet`, and no compound declaration; and `vocabularies/projects.toml`, with the values `teaching` (`Teaching`, `Lehre`), `first-year-practical` (`First-year practical`, `Grundpraktikum`), filed under `teaching`, and `research` (`Research`, `Forschung`).

A procedure-field run copies `tests/fixtures/procedure-fields/` and `tests/fixtures/compounds/` to a fresh temporary directory, copies the fixture reaction types (procedure-validation "Fixture suite") into the procedure-fields copy's `vocabularies/`, writes `tests/fixtures/baseline/OSDB-0100-baseline.md` as the only file of a fresh content root there, applies the stated change (a procedure file named alone is one of that content root, `orgsyndb.toml` and `vocabularies/` those of the procedure-fields copy), and runs `tools/validate.py --static-dir tests/fixtures/static` with `--compounds` set to the registry copy, `--settings` naming the copy of `orgsyndb.toml`, and the content root. "Reports exactly one" counts the stdout lines of the whole run, as for a registry variant run (procedure-validation "Fixture suite").

#### Scenario: The fixture matches its description
- **WHEN** a test reads `tests/fixtures/procedure-fields/orgsyndb.toml` and `tests/fixtures/procedure-fields/vocabularies/`
- **THEN** the declarations and the vocabulary are exactly those stated, and `vocabularies/` holds no other file

