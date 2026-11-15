## Why

A compound has two pages: the site's `/compounds/<key>/`, built from
the collection, with the procedures that make and use it, its
sequences and its routes; and the lab's
`/lab/registry/substances/<key>/`, with the registry record, its stock
and its tasks. The owner sees the site's compound pages as legacy and
wants one substance page, the lab's, since the site no longer needs to
work without the lab. The lab's database already holds every imported
procedure's substrates, products and yields, and the sequences with
their targets, so the lab can show what the site shows without the
build.

This change brings the site's compound page into the lab's substance
page and the compound catalogue's filters into the substance list. A
later change retires the site's compound pages and points their links
to the lab; structure images move into the lab's database in a change
of their own between the two.

## What Changes

- The substance page shows, besides the record, stock and tasks:
  `Hergestellt nach` (`Made by`), the procedures and general-procedure
  entries that make the substance, with yield and status; `Verwendet
  in` (`Used in`), the procedures that start from it, with status;
  `Synthesewege` (`Sequences`), the sequences whose target it is; and
  `Herstellungswege` (`Routes`), its route tree. Procedures and
  sequences link to their pages on the site, compounds in a route tree
  to their substance pages. The SMILES gets the site's copy button.
- The lab derives a substance's route tree from the imported
  procedures that are not withdrawn, by the rules the build uses
  (synthesis-routes "Derived routes").
- The manifest carries each procedure's `status`, which the lab keeps,
  so that it can show the status badge.
- The substance list filters by inventory group and by chemical class,
  each choice including the terms filed under it, beside the search.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-registry`: "Registry pages" adds the four sections, the copy
  button and the list's filters.
- `synthesis-routes`: new "Routes in the lab".
- `build-script`: "manifest subcommand" prints each procedure's
  `status`.
- `collection-import`: "Imported rows" keeps a procedure's `status`.

## Impact

- `tools/pipeline.py` (`manifest_data`).
- `webapp/collection/` (importing, the procedure's `status` and its
  migration, a routes module), `webapp/registry/` (views, templates),
  translations.
- Tests of the manifest, the import, the routes and the registry
  pages; README's substance registry section.
- The builder, which follows `develop`, sends `status` before the lab
  image is rebuilt; the lab ignores keys it does not define, and
  requires `status` once rebuilt.
