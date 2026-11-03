## Context

The validator holds the procedure schema as constants in
`tools/validate.py` (`REQUIRED_KEYS`, `OPTIONAL_KEYS`, `STATUSES`,
`LANGUAGES`, `SHARED_FIELDS`, `SECTIONS_BY_LANGUAGE`, the compound and
sequence keys) and reads the collection's declarations and vocabularies
with `load_fields` and `load_reaction_types`. `pipeline.fields_data`
already turns the declarations into JSON for the site, but in one
language and without what an editor needs: both labels, the vocabulary
names and the options that constrain a value. Python reads no Org
source (build-script "Pipeline helper module").

## Goals / Non-Goals

**Goals:** one call that gives an editor the schema, the declarations,
the vocabularies and the collection's files, in a form that Emacs reads
without a TOML parser; no second copy of the schema.

**Non-Goals:** validation (the index reports no problems beyond a file
it cannot parse); reading Org sources in Python; incremental updates; a
stable format for other consumers.

## Decisions

### JSON from the CLI, not TOML in Elisp

The index is computed by the Python that already parses every TOML file
of a collection and holds the schema. Emacs parses JSON natively.

Rejected: a TOML reader in Elisp. It would parse what `tomllib` already
parses, and the schema would still have to be copied.

### Strict on configuration, lenient on content

Settings, declarations and vocabularies go through the validator's
loaders, so a broken declaration fails the command with the message
`validate` would give. Every other file is reported as it stands: a
compound or a Markdown file that does not parse is listed with `data`
or `front_matter` null and an `error`. An editor is used precisely
while files are broken, and one bad compound must not hide the other
compounds from completion.

### Raw tables, not a digest

Compound files and Markdown front matter appear as parsed, with TOML
dates and times as ISO 8601 strings and the non-finite floats TOML
allows as `null`, which strict JSON readers such as Emacs's accept. The editor picks what it needs;
the index does not have to grow a key each time the editor wants one
more value.

### Org by name only

Org procedures appear with their ID, path and language, which the file
name gives, and `front_matter` null. Reading `#+HUGO_CUSTOM_FRONT_MATTER`
values is Org reading, which belongs to the Elisp front end; the editor
runs in Emacs and reads Org sources there.

Rejected: reading `build/export/`. An export is as old as the last
`export`, and the source being edited is newer by definition.

### No format version

The editor ships in the application repository and is used with the
same checkout, so the index and its reader change together. No version
key is written, and no older shape is read.
