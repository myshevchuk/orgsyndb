## Why

OrgSynDB publishes curated synthetic procedures written in two source
formats, Org by the owner and Markdown by a co-worker who knows neither Org
nor Hugo. Both formats have to reach Hugo as identical TOML front matter.
Nothing in the repository yet says what a procedure's metadata is, and
nothing checks it. The export pipeline (change 2, `add-build-pipeline`) and
the site theme (change 3, `add-site-theme`) both read this metadata, so the
schema and a validator that enforces it have to exist first.

## What Changes

- Define the procedure metadata schema: every front-matter field with its
  TOML type, whether it is required, and its value rules. This includes the
  `OSDB-NNNN` identifier, the `OSDB-NNNN-short-slug` file-name rule, and a
  required `slug` field equal to the lowercased ID, which is how the
  `/procedures/osdb-nnnn/` URL is obtained.
- Add the controlled reaction-type vocabulary `site/data/reaction_types.toml`
  (one table per slug, each with a display `label`). It covers at least
  every reaction type the sample set will use.
- Fix the Org source conventions: the file-level keywords `#+CREATED`,
  `#+LAST_MODIFIED` and `#+AI_MODEL`, their inactive-timestamp format in
  Europe/Berlin local time with the correct English weekday, and how each
  maps to `date`, `lastmod` and `ai_model` in the exported front matter.
- Fix the eight body sections, their headings and their order, for both
  formats.
- Add `templates/procedure.org` and `templates/procedure.md`, whose
  placeholders (`OSDB-0000`, `osdb-0000`, the timestamp and `#+AI_MODEL`
  lines) form the interface that `orgsyndb new` (change 2) fills in.
- Add `tools/validate.py`, a standard-library-only Python 3.14 validator.
  It takes explicit content roots (directories of `+++` TOML front-matter
  Markdown files) plus optional Org source roots. It reports one
  `path:field: severity: message` line per problem and exits `0`, `1` or
  `2`. Its default vocabulary and static paths are resolved from the
  script's own location.
- Add `tests/fixtures/` and a `unittest` suite under `tests/` that runs
  under pytest. The fixtures are:
  - valid procedures;
  - a committed invalid or warning case for each category of rule, each
    failing for exactly one reason;
  - the Org lint and cross-check cases;
  - a baseline procedure from which the tests write the remaining field
    variations into temporary directories.

## Capabilities

### New Capabilities

- `procedure-schema`: what a valid procedure is. This covers identifiers and
  file names, the slug/URL rule, front-matter fields and types, the
  reaction-type vocabulary, Org file-level keywords and their mapping to
  front matter, the body sections, and the two authoring templates.
- `procedure-validation`: how `tools/validate.py` is invoked and what it
  reports. This covers content and Org roots, default paths, file
  discovery, output line format, severities, exit codes, the
  suppression of dependent checks, the Org-to-export cross-check, and the
  fixture suite that proves each rejection.

### Modified Capabilities

None. `openspec/specs/` is empty.

## Impact

- New files: `site/data/reaction_types.toml`, `templates/procedure.org`,
  `templates/procedure.md`, `tools/validate.py`, `tests/fixtures/**`,
  `tests/test_*.py`.
- Interfaces later changes consume:
  - Change 2 (`add-build-pipeline`) invokes the validator with the ox-hugo
    export directory and `md/procedures/` as content roots and
    `org/procedures/` as an Org root.
  - Change 2 mounts exactly those two content directories into the Hugo
    `procedures` section, and nothing else. The validator rejects
    subdirectories, so every published procedure is a top-level file that
    was validated.
  - Change 2 owns export freshness and the removal of exports whose Org
    source was deleted. Its export writes into a directory it empties
    first, or an equivalent mechanism of its choosing. The validator's
    cross-check catches only a missing export or a `date`, `lastmod` or
    `ai_model` mismatch.
  - Its `export.el` produces `date`, `lastmod`, `ai_model` and `slug`
    exactly as specified here, and disables ox-hugo's `author` key.
  - Its `orgsyndb new` fills the template placeholders.
  - Its Hugo config sets the `procedures` permalink to `/procedures/:slug/`
    and declares the `authors`, `reaction_types` and `tags` taxonomies.
- Change 3 (`add-site-theme`) reads the vocabulary labels and the schema
  fields.
- Dependencies: none beyond Python 3.14's standard library (`tomllib`,
  `zoneinfo`, which needs the system tz database) and pytest for the test
  suite. Neither Hugo nor ox-hugo is needed to run the validator or its
  tests.
- Documentation: `docs/SCHEMA.md` is written by the doc writer from this
  change after implementation. It is not an implementation task.
