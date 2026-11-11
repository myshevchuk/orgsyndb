## Context

`lab-registry` gave the lab application the registry and its snapshot,
`GET /lab/registry/snapshot.json` (lab-registry "Snapshot"): `format`
1, a `digest`, the vocabularies `chemical-classes`, `inventory-groups`,
`projects` and `reaction-types`, and the substances with key, names,
short name, group, chemical classes, formula, molar mass, SMILES, CAS
number, note and article number. The demo registry is
`webapp/demo/registry.json`.

On the collection side, `validate.examine_registry` reads
`compounds/<key>.toml` and checks each file; `validate.load_fields`,
`load_terms` and `load_reaction_types` read the declarations in
`orgsyndb.toml` and the files under `vocabularies/`.
`pipeline.fields_data` stages the field data the site reads as
`build/data/fields.json`, `pipeline.index_data` writes the index, and
`pipeline.hugo_overlay` mounts the collection's `compounds/` as Hugo's
`data/compounds`. The site's layouts render a compound's fields from
the field data, without naming any field. Emacs reads `orgsyndb index`,
visits `compounds/<key>.toml` for a definition and can create a
compound file. The container builder clones the collection, polls it
every 300 seconds and builds with the tools.

## Goals / Non-Goals

**Goals:**

- One registry: the collection reads the application's and has none of
  its own.
- The site, the validator, the index and Emacs behave as before for a
  collection whose registry equals its former files.
- A build without the application where the registry is a file: the
  GitHub Pages demo and the tests.

**Non-Goals:**

- Procedures, sequences and the import of the collection into the
  application: a later change.
- Accounts, notebooks and issued ids in the snapshot.
- Configurable presentation of registry fields per collection.

## Decisions

### A collection names its registry

`orgsyndb.toml` gains `registry`, a string: an `http://` or `https://`
address of a snapshot, or a path, relative to the collection, of a
snapshot file. `ORGSYNDB_REGISTRY` in the environment overrides it. A
collection that names none is a configuration error naming `registry`.

`pipeline.registry(collection)` returns the snapshot as a table. For a
path it reads the file. For an address it fetches the snapshot, with a
timeout of 30 seconds, writes it to `build/registry.json` and returns
it; when the fetch fails, it returns the copy in `build/registry.json`
with a warning naming the address and the copy's digest, and without a
copy it raises a configuration error. A snapshot whose `format` is not
1, or that is not a table of the snapshot's keys, is a configuration
error. Every tool takes the registry from this one function: the
validator through `orgsyndb validate`, the build and the index. Beside
the copy it keeps the source it came from in `build/registry.source`,
and falls back to a copy of the same source only.

Alternatives: a registry kept as files beside the collection and
regenerated from the application. It would bring back a second copy
that can drift, which is what this change removes.

### The validator reads a snapshot file

`validate.py --registry FILE` takes the snapshot file in place of
`--compounds DIR`; `orgsyndb validate` passes the file the registry
resolved to (`build/registry.json` for an address). The compound keys
are the substances' keys. Reaction types are the snapshot's
`reaction-types`; a procedure field's `vocabulary` names one of the
snapshot's four vocabularies. The checks of compound files and of
compound declarations go. A substance whose key is `group`, the
directory of the group tabs, is an error on the registry, as a compound
file of that name was.

### Four registry fields replace declared compound fields

`fields.compound` goes from `orgsyndb.toml`. The site's field data
lists, under `compound`, four fields built into the tools, in this
order, with the presentation the demo collection declared for them:

| key | type | label | shown as |
|---|---|---|---|
| `article_number` | text | `Article no.` / `Artikelnr.` | column, search, beside |
| `short_name` | text | `Short name` / `Kurzname` | search, beside |
| `chemical_class` | choice, multiple, `chemical-classes` | `Chemical class` / `Stoffklasse` | column, facet |
| `group` | choice, `inventory-groups` | `Group` / `Gruppe` | facet, tabs |

The layouts render whatever the field data lists, so the fields need no
layout of their own. Procedure field declarations stay in
`orgsyndb.toml`.

### The site reads staged substance data

The build writes `build/data/compounds/<key>.json` for each substance,
holding `name`, `name_de`, `formula`, `mw`, `smiles`, `cas`, the four
fields above (`chemical_class` a list of keys), and `structure_image`,
`structures/<key>.svg` or `.png` when that file exists under
`static/`, the SVG first. Values the substance lacks are left out. Hugo
mounts `build/data/compounds` as `data/compounds` in place of the
collection's `compounds/`. The compound facts and the procedure details
already write a fact only when the compound has it; the compound
catalogue's table and its search text do not, and must leave out a
formula, molar mass or SMILES that a substance lacks.

### The index describes the registry

`index_data` takes `compounds` from the snapshot: one table per
substance with `key`, `data` (as staged for the site) and `url`, the
substance's page in the application,
`<origin>/lab/registry/substances/<key>/` with the origin of the
registry's address, or `null` for a file. `fields.compound` is the four
fields; `vocabularies` the snapshot's four; `schema.compound` goes;
`registry` gives the source and the digest. Emacs completes keys and
shows names from it as before; going to a substance's definition opens
its `url` with `browse-url`, or reports its name and that it has no
page when `url` is `null`. `orgsyndb-new-compound` goes, and so does
completion in compound files.

### The builder fetches the snapshot

`orgsyndb-deploy` requests the snapshot itself at
`ORGSYNDB_REGISTRY_URL`, by default
`http://app:8000/lab/registry/snapshot.json`, sending as `Host` the
first concrete entry of `ORGSYNDB_ALLOWED_HOSTS` (not `*`, a leading `.`
dropped), or `localhost`, so the application accepts the request
without a setting of its own; the builder and `app` share
`orgsyndb.env`. It keeps the snapshot in `<data>/registry.json` with its
address, and runs every `tools/orgsyndb` of the cycle with
`ORGSYNDB_REGISTRY` naming that file, so the site and the index
describe one registry and the build itself fetches nothing. The
snapshot's digest is part of each combination the cycle builds and
records, so a changed registry is built like a new commit. When `app`
cannot be reached the cycle uses the copy of the same address.

### Demo and test collections

`examples/demo/orgsyndb.toml` names `../../webapp/demo/registry.json`.
The test collection's `registry.json` is a copy of the demo registry.
The fixture registry `tests/fixtures/registry.json` is made once from
the former fixture compound files, which set no group or class: each
substance gets the group `reagents` and the chemical class
`organic-compounds`, beside the fixture reaction types and projects. `lab-registry`'s test that
compared the demo registry with an import of `examples/demo` goes; the
tests of `registry_import` use a small collection in the old layout
under `webapp/tests/`.

## Risks / Trade-offs

- [A build needs the application or a cached copy] → The cache keeps
  builds working through an outage; a collection without either stops
  with a configuration error that names the address.
- [Presentation no longer configurable] → A collection cannot hide the
  article number or add a column of its own. The four fields are those
  the only real collection declared; configuration can return if a
  second collection needs it.
- [The `in_house` and `stock` facets go] → They were values of compound
  files the registry does not keep (made or bought is per lot; stock
  is the lots'). The site can derive "made in house" from the
  procedures later.
- [Keys `group` and the tab directory] → A substance named `group`
  would shadow the tab pages; the validator refuses it, as before.
