## Why

The lab application knows a compound only by matching text against the
collection index: a task's free-text product, an item's or lot's article
number and an item's typed name are looked up through `compound_for`,
and a compound the index lacks leaves the record without one. Two
records name the same substance only when their texts happen to match,
the index can change under them, and the application has no identity of
its own for a substance and no way to edit one: a new substance is a
file in the collection, or a free-text name on an item. The owner has decided
that the database becomes the registry: substances and every vocabulary
are created and edited in the application, and records refer to them
by foreign key. This change is the application half of that; a second
change makes the collection read the registry instead of its own
compound and vocabulary files.

## What Changes

- New package `registry`: substances, each with a fixed `key`, names in
  both languages, a short name, a required group, one or more chemical
  classes, and an optional formula, molar mass, SMILES and CAS number.
  A mixture or a solution taken as one is a substance of its own.
- New package `vocabulary`: chemical classes, groups and projects, each
  a tree of terms, and reaction types, a flat list; each term has a
  fixed `key` and labels in both languages.
- Pages and forms for substances and vocabularies under `/lab/registry/`,
  readable without sign-in, editable when signed in, with change
  history and an admin.
- The registry as one JSON document, the snapshot, served at
  `/lab/registry/snapshot.json` with a digest, and loaded by
  `manage.py registry_load`; `manage.py registry_import` fills an empty
  registry from a collection's `compounds/` and `vocabularies/`.
- **BREAKING** Inventory records refer to substances: an article is one
  substance and carries the article number and category; an item is a
  container size of an article and loses its own article number, name
  and category; a lot is of any substance, made or bought, with an
  optional supplier, and loses its article number. The `inventory`
  field goes from items and lots.
- **BREAKING** A task names its substance instead of a free-text
  product.
- Planning matches tasks and articles by substance, and a task and a
  lot by batch and substance; molar masses come from the substance.
- The application no longer reads compounds from the collection index;
  it still reads the language, the procedures and the sequences.
  Wherever a substance shows, its name links to its page in the
  application, which links to the site's compound page when the index
  lists the key.
- The demo data set keeps its registry in the application's own
  package and loads it before the lab records.
- The table diagram places the new tables.

## Capabilities

### New Capabilities

- `lab-registry`: substances and vocabularies kept in the application,
  their pages, forms, admin, the snapshot, and the commands that load
  and import a registry.

### Modified Capabilities

- `end-product-inventory`: articles; items as container sizes of an
  article; lots of any substance, made or bought; the lists, pages and
  forms that showed an item's name, article number or compound.
- `task-tracker`: a task's substance replaces its product.
- `production-planning`: matching by substance, and batches between a
  task and a lot by substance.
- `web-app`: the collection index without compounds; substance links
  replace compound links; the navigation's registry entry.
- `lab-demo`: the demo registry, and the records of the data set in
  terms of substances.
- `lab-overview`: names come from substances.
- `database-diagram`: the new packages and tables in the drawing.

## Impact

- New: `webapp/registry/`, `webapp/vocabulary/` with migrations,
  templates, forms, views, admin and tests; `webapp/demo/registry.json`.
- Changed: `inventory` models with a migration that replaces the old
  tables (the application has no users; no data is carried over),
  bookings, figures, forms, views, templates and admin; `tasks` models,
  forms, views and templates; `planning.plan`; `orgsyndb_web.index`,
  its template tag and the navigation; the demo data set and command;
  the schema diagram's grid and its generated page; the German
  translations; their tests.
- Docs: `README.md`, on the registry and its commands; the generated
  table diagram.
- Unchanged here, changed by the collection change that follows:
  `compounds/`, `vocabularies/` and declared compound fields in
  collections, the validator, the export, the site and Emacs.
