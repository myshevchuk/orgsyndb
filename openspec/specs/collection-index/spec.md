# collection-index Specification

## Purpose
Describe a collection for an editor in one JSON table: the schema keys the validator knows, the declared fields and their vocabularies, and every compound, procedure and sequence file with what Python can parse of it.
## Requirements
### Requirement: Index data
`pipeline.index_data(collection)` SHALL return the index of the collection directory `collection`: a table that `json.dumps` serializes, with these keys and nothing else.

- `site_language`: `pipeline.site_language(<app>/site)`.
- `schema`: the keys the validator knows without the collection's declarations.
  - `procedure`: `required` and `optional`, the required and optional top-level keys in the validator's order; `entry`, the keys of a scope entry, `substrates`, `products`, `scale`, `time`, `temperature` and `note`; `product`, the keys of a product table, `compound` and `yield_percent`; `statuses`; `languages`; `shared`, the keys every variant of a procedure shares before declared fields are added; and `sections`, a table mapping each language to its eight body section names in order.
  - `compound`: `required` and `optional`, the built-in compound keys.
  - `sequence`: `keys`, the sequence keys, and `step`, the keys of a step, `procedure` and `entry`.
- `fields`: a table of `compound` and `procedure`, each listing the collection's declarations of that entity in declared order, each as a table of `key`, `type`, `label`, `label_de`, `required`, `column` for a compound field, and the options of its type as written in `orgsyndb.toml`: `pattern`, `unique`, `search` and `beside` for text; `min`, `max`, `unit`, `unique` and `beside` for number; `facet` for boolean; `vocabulary`, `multiple`, `facet` and `tabs` for choice. Defaults are applied: an absent flag is `false`, and an absent `label_de`, `pattern`, `min`, `max` or `unit` is `null`. A procedure declaration carries none of `column`, `search`, `tabs` and `beside`.
- `vocabularies`: a table mapping each vocabulary that a declaration names, and `reaction-types` when `vocabularies/reaction-types.toml` exists, to a table mapping each of its values, in file order, to a table of `label`, `label_de` and `parent`, the last two `null` when absent.
- `compounds`: one table per entry of `compounds/` whose name is `<key>.toml` with a key the registry accepts, ordered by key. Each holds `key`, `path` (`compounds/<key>.toml`) and `data`, the file's table as parsed. When the file cannot be read as UTF-8 TOML, `data` is `null` and `error` holds the reason as the validator words it.
- `procedures`: one table per entry of `org/procedures/` with suffix `.org` and of `md/procedures/` with suffix `.md` whose name the validator's procedure file-name pattern accepts, ordered by ID and then by path. Each holds `id` and `language`, both from the file name, `language` being `null` for a name without a code; `path`, relative to the collection; `format`, `org` or `md`; and `front_matter`. For a Markdown file `front_matter` is its front matter as parsed, or `null` with the reason in `error` when the file cannot be read or has no valid front matter. For an Org file `front_matter` is always `null` and no `error` is given, since Python reads no Org source.
- `sequences`: one table per entry of `md/sequences/` with suffix `.md` whose name the validator's sequence file-name pattern accepts, ordered by ID and then by path, each holding `id`, `language`, `path` and `front_matter` as for a Markdown procedure.

Paths use `/`. A directory that does not exist contributes nothing. TOML date, time and date-time values appear as their ISO 8601 text, as Python's `isoformat` writes them. A float that is not finite, which TOML writes `nan`, `inf` or `-inf`, appears as `null` wherever it occurs, so the table serializes to strict JSON, with no `NaN` or `Infinity`. Entries that a pattern above does not accept, dotfiles and subdirectories are left out without a report. `index_data` reads no Org file and writes nothing. It raises `validate.ConfigError` when the declarations or their vocabularies break a rule of `validate.load_fields`, or the reaction types one of `validate.load_reaction_types`.

#### Scenario: Index of the test collection
- **WHEN** a test calls `index_data` on a copy of `tests/fixtures/collection/`
- **THEN** `compounds` lists the 20 compound keys in sorted order, and the entry of `acetic-anhydride` has `path` `compounds/acetic-anhydride.toml` and `data.name_de` `Essigsäureanhydrid`
- **AND** `procedures` lists 18 Markdown files, the entry of `md/procedures/OSDB-0002-aspirin.de.md` has `id` `OSDB-0002`, `language` `de` and `format` `md`, and that of `md/procedures/OSDB-0002-aspirin.md` has `language` `null`, `front_matter.status` `draft` and `front_matter.date` `2026-10-19T23:46:11+02:00`
- **AND** `sequences` lists 4 files
- **AND** the keys of `fields.procedure` are `notebook`, `project`, `working_time` and `inert_atmosphere` in that order, the `project` declaration has `vocabulary` `projects`, and no procedure declaration has the key `column`
- **AND** `vocabularies` holds `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`

#### Scenario: Schema keys
- **WHEN** a test calls `index_data` on a copy of the test collection
- **THEN** each list of `schema` equals the validator constant it comes from: `procedure.required` `validate.REQUIRED_KEYS`, `procedure.optional` `validate.OPTIONAL_KEYS`, `procedure.entry` and `procedure.product` the scope-entry and product keys that `check_scope` and `check_products` accept, `procedure.statuses` `validate.STATUSES`, `procedure.languages` `validate.LANGUAGES`, `procedure.shared` `validate.SHARED_FIELDS`, each list of `procedure.sections` its entry of `validate.SECTIONS_BY_LANGUAGE`, `compound.required` and `compound.optional` `validate.COMPOUND_REQUIRED_KEYS` and `validate.COMPOUND_OPTIONAL_KEYS`, and `sequence.keys` and `sequence.step` `validate.SEQUENCE_KEYS` and `validate.STEP_KEYS`
- **AND** `schema.procedure.statuses` is `["draft", "checked", "retired"]`, `schema.procedure.sections.de` begins with `Zusammenfassung`, and `schema.compound.required` is `["name", "formula", "mw", "smiles"]`

#### Scenario: Non-finite numbers
- **WHEN** a test writes `compounds/odd.toml`, a valid compound file whose `mw` is `nan` and that also holds `limits = [inf, -inf, 1.5]`, into a copy of the test collection and calls `index_data`
- **THEN** the entry of `odd` has `data.mw` `null` and `data.limits` `[null, null, 1.5]`, and `json.dumps` of the index with `allow_nan=False` succeeds

#### Scenario: Org procedures by name
- **WHEN** a test calls `index_data` on a copy of the demo collection
- **THEN** the entry of `org/procedures/OSDB-0007-ethyl-cinnamate.de.org` has `id` `OSDB-0007`, `language` `de`, `format` `org` and `front_matter` `null`, and no Org entry has the key `error`

#### Scenario: Broken content files are listed
- **WHEN** a test writes `compounds/broken.toml` holding `name = ` and `md/procedures/OSDB-0990-broken.md` holding no front matter into a copy of the test collection, together with `md/procedures/notes.txt` and `md/procedures/OSDB-12-short.md`, and calls `index_data`
- **THEN** the entry of `broken` has `data` `null` and an `error` containing `TOML`, the entry of `OSDB-0990` has `front_matter` `null` and an `error`, the other 20 compounds still carry their data, and neither `notes.txt` nor `OSDB-12-short.md` is listed

#### Scenario: Empty collection
- **WHEN** a test calls `index_data` on a directory holding only `orgsyndb.toml` with `format = 1`
- **THEN** `compounds`, `procedures` and `sequences` are empty lists, `fields.compound` and `fields.procedure` are empty lists, and `vocabularies` is an empty table

#### Scenario: Broken declaration
- **WHEN** a test removes `vocabularies/projects.toml` from a copy of the test collection and calls `index_data`
- **THEN** it raises `validate.ConfigError` naming `projects`

#### Scenario: Nothing written
- **WHEN** a test calls `index_data` on a copy of the demo collection that has no `build/`
- **THEN** the copy still has no `build/`, and no file of the copy changed

