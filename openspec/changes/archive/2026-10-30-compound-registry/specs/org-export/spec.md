## MODIFIED Requirements

### Requirement: Exported front matter
The export of each Org source `<stem>.org` SHALL be a file `<stem>.md` with `+++` TOML front matter that meets all of the following:
- `date`, `lastmod`, `ai_model`, `slug` and the absence of `author` follow the procedure-schema mapping.
- Every key whose value is a table or an array of tables, such as `products`, is written after all other keys, whatever its position among the source's `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- Every other front-matter key and value is ox-hugo's own output.

The export adds its own `#+DATE`, `#+HUGO_LASTMOD`, `#+EXPORT_FILE_NAME` and, for a source whose `#+AI_MODEL` names a model, `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model` lines at the top of an in-memory copy of the source. It exports with point at the beginning of that buffer, so that no heading's `CLOSED` timestamp is taken as the date. The source itself can set none of these values (procedure-schema "Exported values come only from the file-level keywords").

Before exporting, the export checks that `org-hugo--gen-front-matter`, `tomelr-toml-table-p` and `tomelr-toml-table-array-p` are defined. If one is not, it exits non-zero with a message naming the missing function.

#### Scenario: Seed export validates cleanly
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` and then `tools/validate.py build/export md/procedures` in the collection copy
- **THEN** the validator exits 0 and prints nothing to stdout

#### Scenario: Table written first in the source is emitted last
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0901-table-first.org`, whose first `#+HUGO_CUSTOM_FRONT_MATTER:` line sets `:products` to two products and whose later lines set `:scale`, `:hazards` and `:substrates`
- **THEN** `tomllib` parses its export with `scale`, `hazards` and `substrates` as top-level keys
- **AND** `products` is an array of two tables holding exactly the keys and values the source's `:products` list gives, in its order

#### Scenario: AI model mapping
- **WHEN** an integration test exports one source whose `#+AI_MODEL` is `none`, one without `#+AI_MODEL` and one whose `#+AI_MODEL` is `example-model-1`
- **THEN** the first two exports have no `ai_model` key, and the third has `ai_model = "example-model-1"`
- **AND** no export has an `author` key

#### Scenario: Seconds survive
- **WHEN** an integration test exports a source whose `#+LAST_MODIFIED` is `[2026-10-19 Mon 21:00:07]`
- **THEN** its export's `lastmod` parses with `tomllib` to an offset datetime equal to `2026-10-19T21:00:07+02:00`
