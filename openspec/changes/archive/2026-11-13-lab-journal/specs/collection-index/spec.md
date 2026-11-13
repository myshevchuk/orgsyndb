## MODIFIED Requirements

### Requirement: Index data
`pipeline.index_data(collection)` SHALL return the index of the collection directory `collection`: a table that `json.dumps` serializes, with these keys and nothing else. It reads the collection's registry as compound-registry "Reading the registry" states, without storing a copy.

- `site_language`: `pipeline.site_language(<app>/site)`.
- `schema`: the keys the validator knows without the collection's declarations.
  - `procedure`: `required` and `optional`, the required and optional top-level keys in the validator's order; `entry`, the keys of a scope entry, `substrates`, `products`, `scale`, `time`, `temperature` and `note`; `product`, the keys of a product table, `compound` and `yield_percent`; `statuses`; `languages`; `shared`, the keys every variant of a procedure shares before declared fields are added; and `sections`, a table mapping each language to its eight body section names in order.
  - `sequence`: `keys`, the sequence keys, and `step`, the keys of a step, `procedure`, `product`, `substrates` and `products`.
- `registry`: a table of `source`, the registry's address or path as the collection or `ORGSYNDB_REGISTRY` names it, and `digest`, the snapshot's `digest`.
- `fields`: a table of `compound` and `procedure`. `compound` lists the four registry fields (compound-fields "Registry fields") in their order, each as a table of `key`, `type`, `label`, `label_de`, `column`, and the options of its type: `search` and `beside` for text, `vocabulary`, `multiple`, `facet` and `tabs` for choice. `procedure` lists the journal fields (procedure-fields "Journal fields") and then the collection's procedure declarations in declared order, each as a table of `key`, `type`, `label`, `label_de`, `required`, and the options of its type as written in `orgsyndb.toml`: `pattern` and `unique` for text; `min`, `max`, `unit` and `unique` for number; `facet` for boolean; `vocabulary`, `multiple` and `facet` for choice. Defaults are applied: an absent flag is `false`, and an absent `label_de`, `pattern`, `min`, `max` or `unit` is `null`.
- `accounts`: the registry's accounts, as the snapshot lists them, each a table of `username` and `name`;
- `notebooks`: the registry's notebooks, as the snapshot lists them, each a table of `code` and `user`;
- `vocabularies`: a table mapping each of the registry's vocabularies, `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`, to a table mapping each of its terms, in the snapshot's order, to a table of `label`, `label_de` and `parent`, the last two `null` when absent.
- `compounds`: one table per substance of the registry, ordered by key. Each holds `key`; `data`, the substance's values as the build stages them for the site (site-build "Hugo configuration"); and `url`, the substance's page in the lab application, `<origin>/lab/registry/substances/<key>/` with the scheme, host and port of the registry's address, or `null` when the registry is a file.
- `procedures`: one table per entry of `org/procedures/` with suffix `.org` and of `md/procedures/` with suffix `.md` whose name the validator's procedure file-name pattern accepts, ordered by ID and then by path. Each holds `id` and `language`, both from the file name, `language` being `null` for a name without a code; `path`, relative to the collection; `format`, `org` or `md`; and `front_matter`. For a Markdown file `front_matter` is its front matter as parsed, or `null` with the reason in `error` when the file cannot be read or has no valid front matter. For an Org file `front_matter` is always `null` and no `error` is given, since Python reads no Org source.
- `sequences`: one table per entry of `md/sequences/` with suffix `.md` whose name the validator's sequence file-name pattern accepts, ordered by ID and then by path, each holding `id`, `language`, `path` and `front_matter` as for a Markdown procedure.

Paths use `/`. A directory that does not exist contributes nothing. TOML date, time and date-time values appear as their ISO 8601 text, as Python's `isoformat` writes them. A float that is not finite, which TOML writes `nan`, `inf` or `-inf`, appears as `null` wherever it occurs, so the table serializes to strict JSON, with no `NaN` or `Infinity`. Entries that a pattern above does not accept, dotfiles and subdirectories are left out without a report. `index_data` reads no Org file and writes nothing. It raises `validate.ConfigError` when the registry cannot be read (compound-registry "Reading the registry") or when the procedure declarations break a rule of `validate.load_fields`.

#### Scenario: Index of the test collection
- **WHEN** a test calls `index_data` on a copy of `tests/fixtures/collection/`
- **THEN** `compounds` lists the 21 substance keys of its registry in sorted order, the entry of `acetic-anhydride` has `data.name_de` `Essigsäureanhydrid` and `url` `null`, and `registry.source` is the path the collection names
- **AND** `procedures` lists 18 Markdown files, the entry of `md/procedures/OSDB-0002-aspirin.de.md` has `id` `OSDB-0002`, `language` `de` and `format` `md`, and that of `md/procedures/OSDB-0002-aspirin.md` has `language` `null`, `front_matter.status` `draft` and `front_matter.date` `2026-10-19T23:46:11+02:00`
- **AND** `sequences` lists 4 files
- **AND** the keys of `fields.procedure` are `notebook`, `project`, `working_time` and `inert_atmosphere` in that order, the `project` declaration has `vocabulary` `projects`, and the keys of `fields.compound` are `article_number`, `short_name`, `chemical_class` and `group`, and `notebooks` lists `AE-1`, `AE-2`, `CE-1` and `CE-3`
- **AND** `vocabularies` holds exactly `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`

#### Scenario: Pages of a registry at an address
- **WHEN** a test serves the test collection's registry at `http://127.0.0.1:<port>/lab/registry/snapshot.json` and calls `index_data` on a copy of the collection that names that address
- **THEN** the entry of `acetic-anhydride` has the `url` `http://127.0.0.1:<port>/lab/registry/substances/acetic-anhydride/`, `registry.digest` is the snapshot's digest, and the copy has no `build/registry.json`

#### Scenario: Schema keys
- **WHEN** a test calls `index_data` on a copy of the test collection
- **THEN** each list of `schema` equals the validator constant it comes from: `procedure.required` `validate.REQUIRED_KEYS`, `procedure.optional` `validate.OPTIONAL_KEYS`, `procedure.entry` and `procedure.product` the scope-entry and product keys that `check_scope` and `check_products` accept, `procedure.statuses` `validate.STATUSES`, `procedure.languages` `validate.LANGUAGES`, `procedure.shared` `validate.SHARED_FIELDS`, each list of `procedure.sections` its entry of `validate.SECTIONS_BY_LANGUAGE`, and `sequence.keys` and `sequence.step` `validate.SEQUENCE_KEYS` and `validate.STEP_KEYS`; `schema` has no key `compound`
- **AND** `schema.procedure.statuses` is `["draft", "checked", "retired"]` and `schema.procedure.sections.de` begins with `Zusammenfassung`

#### Scenario: Non-finite numbers
- **WHEN** a test writes `md/procedures/OSDB-0990-odd.md`, a procedure whose front matter holds `limits = [inf, -inf, 1.5]` and `working_time = nan`, into a copy of the test collection and calls `index_data`
- **THEN** the entry of `OSDB-0990` has `front_matter.working_time` `null` and `front_matter.limits` `[null, null, 1.5]`, and `json.dumps` of the index with `allow_nan=False` succeeds

#### Scenario: Org procedures by name
- **WHEN** a test calls `index_data` on a copy of the demo collection
- **THEN** the entry of `org/procedures/OSDB-0007-ethyl-cinnamate.de.org` has `id` `OSDB-0007`, `language` `de`, `format` `org` and `front_matter` `null`, and no Org entry has the key `error`

#### Scenario: Broken content files are listed
- **WHEN** a test writes `md/procedures/OSDB-0990-broken.md` holding no front matter into a copy of the test collection, together with `md/procedures/notes.txt` and `md/procedures/OSDB-12-short.md`, and calls `index_data`
- **THEN** the entry of `OSDB-0990` has `front_matter` `null` and an `error`, and neither `notes.txt` nor `OSDB-12-short.md` is listed

#### Scenario: Empty collection
- **WHEN** a test calls `index_data` on a directory holding only `orgsyndb.toml` with `format = 1` and a `registry` naming a snapshot file without substances or terms
- **THEN** `compounds`, `procedures` and `sequences` are empty lists, `fields.procedure` lists the two journal fields, `fields.compound` lists the four registry fields, and every vocabulary is an empty table

#### Scenario: A declaration names a missing vocabulary
- **WHEN** a test adds a declaration with `key = "funding"`, `type = "choice"`, `label = "Funding"` and `vocabulary = "storage"` to a copy of the test collection's `orgsyndb.toml` and calls `index_data`
- **THEN** it raises `validate.ConfigError` naming `storage`

#### Scenario: Nothing written
- **WHEN** a test calls `index_data` on a copy of the demo collection that has no `build/`
- **THEN** the copy still has no `build/`, and no file of the copy changed
