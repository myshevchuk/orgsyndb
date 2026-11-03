## Why

An editor that completes front-matter keys and values, compound keys and
procedure IDs needs what the validator knows: the schema's keys, the
collection's declared fields and vocabularies, its compounds, procedures
and sequences. Emacs, the first such editor, has no TOML reader, and a
copy of the schema in Elisp would drift from the validator's tables. One
command that prints the collection as JSON keeps those tables the only
source and gives an editor everything in one call.

## What Changes

- A new subcommand, `orgsyndb index`, prints one JSON document
  describing the collection and exits. It writes nothing, starts no
  step, and needs no external tool, so it works without Emacs, Hugo or
  Git.
- `pipeline.index_data(collection)` builds that document:
  - the site language;
  - the built-in schema keys: procedure keys, required and optional,
    scope-entry and product keys, statuses, languages, the keys variants
    share, and the section names of each language; compound keys;
    sequence and step keys;
  - the declared compound and procedure fields with their options;
  - the vocabularies those fields name, and the reaction types;
  - every compound file, with its parsed table;
  - every procedure and sequence file, with its ID, language and format,
    and the parsed front matter of each Markdown file.
- The index reads content leniently: a compound or Markdown file that
  does not parse is listed with the reason and no data. The settings,
  the declarations and the vocabularies are read as strictly as the
  validator reads them, and a configuration error stops the command.
- Org procedures are listed by file name only, with no front matter:
  Python still reads no Org source. An editor reads the Org source
  itself.
- The validator names the keys of a scope entry and of a product as
  constants, which its checks and the index share.

## Capabilities

### New Capabilities

- `collection-index`: the index data and what it holds.

### Modified Capabilities

- `build-script`: the `index` subcommand, its place among the
  subcommands, the tools it needs, and `index_data` among the pipeline
  functions.
- `collection`: `index` works on a collection.

## Impact

- Code: `tools/pipeline.py` (`index_data`), `tools/orgsyndb` (the
  subcommand and its usage line), `tools/validate.py` (the scope-entry
  and product key constants).
- Tests: a new `tests/test_index.py` on copies of the test collection
  and the demo.
- Docs: the README's command list (doc writer).
- No change to the build, the validator's findings or the site.
