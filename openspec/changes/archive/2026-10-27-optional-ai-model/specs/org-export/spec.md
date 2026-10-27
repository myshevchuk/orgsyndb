## MODIFIED Requirements

### Requirement: Exported front matter
The export of each Org source `<stem>.org` SHALL be a file `<stem>.md` with `+++` TOML front matter that meets all of the following:
- `date`, `lastmod`, `ai_model`, `slug` and the absence of `author` follow the procedure-schema mapping.
- Every key whose value is a table is written after all other keys, whatever its position among the source's `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- Every other front-matter key and value is ox-hugo's own output.

The export adds its own `#+DATE`, `#+HUGO_LASTMOD`, `#+EXPORT_FILE_NAME` and, for a source whose `#+AI_MODEL` names a model, `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model` lines at the top of an in-memory copy of the source. It exports with point at the beginning of that buffer, so that no heading's `CLOSED` timestamp is taken as the date. The source itself can set none of these values (procedure-schema "Exported values come only from the file-level keywords").

Before exporting, the export checks that `org-hugo--gen-front-matter` and `tomelr-toml-table-p` are defined. If either is not, it exits non-zero with a message naming the missing function.

#### Scenario: Seed export validates cleanly
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` and then `tools/validate.py build/export md/procedures` in the collection copy
- **THEN** the validator exits 0 and prints nothing to stdout

#### Scenario: Table written first in the source is emitted last
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0901-table-first.org`, whose first `#+HUGO_CUSTOM_FRONT_MATTER:` line sets `:product` and whose later lines set `:scale`, `:yield_percent`, `:hazards` and `:precursors`
- **THEN** `tomllib` parses its export with `scale`, `yield_percent`, `hazards` and `precursors` as top-level keys
- **AND** the `product` table holds exactly the keys the source's `:product` map gives

#### Scenario: AI model mapping
- **WHEN** an integration test exports one source whose `#+AI_MODEL` is `none`, one without `#+AI_MODEL` and one whose `#+AI_MODEL` is `example-model-1`
- **THEN** the first two exports have no `ai_model` key, and the third has `ai_model = "example-model-1"`
- **AND** no export has an `author` key

#### Scenario: Seconds survive
- **WHEN** an integration test exports a source whose `#+LAST_MODIFIED` is `[2026-10-19 Mon 21:00:07]`
- **THEN** its export's `lastmod` parses with `tomllib` to an offset datetime equal to `2026-10-19T21:00:07+02:00`

### Requirement: Org front-end library
`tools/osdb-org.el` SHALL hold every function of the export that reads Org text or Org file names, together with the timestamp arithmetic, and loading it SHALL have no effect beyond defining its functions and constants. It loads neither Org nor ox-hugo nor tomelr. It reads no command-line argument, starts no export and never calls `kill-emacs`. It provides the feature `osdb-org`, and `tools/export.el` loads it from its own directory after making the settings of "Isolated batch Emacs". It defines at least the functions that the ERT scenarios of this capability, procedure-schema and localization call: `osdb-org-examine`, `osdb-org-problem-line`, `osdb-org-check-file-name`, `osdb-org-local-instants`, `osdb-org-export-instants`, `osdb-org-rfc3339` and `osdb-org-zone-available-p`.

`osdb-org-examine` takes a directory and returns a pair of the sources and the problems, as follows:
- The sources are the Org sources without any problem, in name order. Each carries its absolute path, its stem (the file name without `.org`), its `date` and `lastmod` as `YYYY-MM-DDThh:mm:ss+HH:MM` strings, and its AI model, or none when `#+AI_MODEL` is absent or `none`.
- The problems are path and problem pairs, in report order. Each problem has a field, a severity and a message.

#### Scenario: Library loads alone
- **WHEN** an ERT test, running in the suite's `emacs -Q --batch` after it loaded `tools/osdb-org.el`, checks which features are present
- **THEN** `osdb-org` is a feature, and `org`, `ox-hugo` and `tomelr` are not
