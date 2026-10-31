## Context

The compound registry fixes a compound's keys in the validator, and the
compound page and directory name each of them in their layouts. A
collection is the group's data; the application is shared. Further
changes, listed in `openspec/STATE.md`, will build on what is declared
here: facets and search on the compound directory, tabs, procedure
fields, reaction types as a collection vocabulary, and compound fields
shown where procedures name a compound. The declaration format has to
carry those without being rewritten.

## Decisions

- **Declarations live in `orgsyndb.toml`.** The file already is the
  collection's settings. `fields.compound` names the entity, so that
  `fields.procedure` can join it later.
- **An array of tables, in display order.** Hugo ranges over a map in
  sorted key order, so a table keyed by field would lose the order the
  group chose; a list keeps it.
- **Flat keys in the compound file.** A declared field is written like
  `cas`: `item_number = "CH-0007"`. A `[custom]` sub-table would put
  every key written after its header into it, a mistake easy to make
  in a hand-edited file. The cost is that a declaration may not take a
  built-in key, which the validator refuses, and that a future built-in
  key may collide with a group's field, which the validator will then
  report.
- **Keys ending in `_de` are reserved**, so that a translated text
  value can later follow `name_de`'s pattern.
- **Four types.** `text`, `number`, `boolean` and `choice` cover item
  numbers, short names, quantities, flags and classifications. Only a
  choice has a known set of labelled values, which facets and tabs
  will need. Dates and links wait for a field that needs them.
- **Vocabularies are files of their own**, shaped like
  `site/data/reaction_types.toml`: one table per value with `label` and
  `label_de`. A long classification does not crowd the settings file,
  two fields may share a vocabulary, and the reaction types can later
  become one of them.
- **Levels through `parent`.** Each value names its parent, so every
  value keeps one flat, unique key that a compound file, an address or
  a facet can name, and the file keeps the shape of the reaction-type
  vocabulary. A value may be assigned at any level.
- **Two checks of `orgsyndb.toml`.** The program checks only what it
  needs to find the collection, `format` and the top-level keys, so
  `clean`, `new` and `init` never depend on the declarations. The
  validator applies the same shallow check and then checks the
  declarations, as it checks the reaction-type vocabulary, as a
  configuration error. It gains `--settings` so that it can be run on
  its own: an omitted option falls back to the working directory's
  `orgsyndb.toml`, which may be missing, as its other collection paths
  may, but a file the option names must exist, so that a mistyped path
  cannot switch every check of declared fields off.
- **The build stages resolved field data.** The pipeline already
  stages procedures in the site's language; it does the same for the
  declarations, choosing labels and resolving each value's path, and
  writes JSON that Hugo mounts as data. The layouts then only print:
  they never parse the settings file, apply defaults or walk a
  hierarchy.
- **Patterns are Python regular expressions**, matched whole by the
  validator. Hugo never applies them.
- **The page shows a value's path, the directory its label.** On a
  compound page there is room for `Carbonyl compounds › Ketones`; a
  table column shows `Ketones`.
- **No facets, tabs or search here.** A declaration may not yet say
  `facet` or `tabs`; those options arrive with the changes that give
  them meaning, and until then the validator refuses them as unknown.

## Alternatives rejected

- **A schema file inside `compounds/`.** The registry rejects any file
  not named `<key>.toml`, and Hugo mounts the whole directory as
  compound data, so the schema would appear as a compound.
- **Fields declared in the application**, like
  `site/data/reaction_types.toml`. The fields are the group's, and two
  collections built by one application would have to agree on them.
- **A table keyed by field name.** Loses the declared order in Hugo.
- **Custom fields under a `[custom]` sub-table.** Safe from collisions,
  but a key written below the header by mistake changes meaning.
- **Values listed inside the declaration.** Verbose for long lists,
  not shareable between fields, and unlike the reaction-type
  vocabulary.
- **Nested tables for levels** (`[carbonyl-compounds.ketones]`). A
  value's identity would become its path, an address or facet would
  have to name the path, and moving a value would change its key.
- **The program checking declarations before every subcommand.** A
  broken vocabulary would then block `clean`.
- **Labels chosen in the layouts.** Possible, as compound names are,
  but the layouts would also have to walk the hierarchy to write a
  path; the pipeline does both once.
