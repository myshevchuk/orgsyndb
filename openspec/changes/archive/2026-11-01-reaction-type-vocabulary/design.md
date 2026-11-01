## Context

`site/data/reaction_types.toml` is the one collection-specific list
still inside the application. The validator loads it with its own
loader (`load_vocabulary`), defaulting to the application's copy, or
the file `--vocabulary` names. Hugo reads it through mount 5 of the
overlay (`<site>/data` → `data`), and `reaction-type-label.html` picks
`label_<lang>` or `label` from it. Since the field declarations, the
collection has `vocabularies/`, read by `load_terms` from beside the
settings file, and the build hands Hugo normalised data under
`build/data/`, mounted as `site.Data.collection`.

## Goals / Non-Goals

**Goals:**
- Each collection names its own reaction types, in the vocabulary
  format it already uses for declared fields.
- One reading of the file serves the validator and the site.
- A new collection starts with a usable list.

**Non-Goals:**
- Nested reaction types. The facet, the term pages and the sequence
  steps would all need the tree treatment the declared facets have.
- More than one reaction type per procedure.
- Moving `status` or the general-procedure `kind` into vocabularies.

## Decisions

**A fixed file name, not a declaration.** The reaction types are
`vocabularies/reaction-types.toml`; nothing in `orgsyndb.toml` names
them. `reaction_types` is a built-in key with built-in behaviour (a
Hugo taxonomy, a facet, a column, the sequence steps), so a setting
that could point elsewhere would only add a way to get it wrong.
Rejected: `[procedures] reaction_types = "<name>"` in the settings
file.

**The vocabulary format, without `parent`.** The file follows
compound-fields "Vocabularies", so it gains the checks those files
have, such as no unknown entry key, and loses the old loader's
tolerance for stray keys. `parent` is refused because nothing on the
site would show the levels. Rejected: accepting `parent` and ignoring
it, which would let a collection write a tree the site silently
flattens.

**A missing file means no reaction type.** As with a missing registry,
each procedure then reports `unknown reaction type`, naming the file
to create, and a collection of compounds alone validates. Rejected: a
configuration error, which would stop every run, the compound checks
included, of a collection that has no procedures yet.

**`--vocabulary` goes; the settings file decides.** Every other
vocabulary resolves against the directory of the settings file, so the
reaction types do too. An override for this one file would let the
validator and a declared field naming `reaction-types` read two
different files. The fixture run passes `--settings` naming a fixture
settings file, `tests/fixtures/settings/orgsyndb.toml`, beside the
fixture reaction types. Field-declaration and procedure-field runs copy
those reaction types into their copy's `vocabularies/`. Rejected:
keeping `--vocabulary` with a new default, a second path to the same
data that only tests would use.

**A declared field naming `reaction-types` needs the file.** Such a
field reads the vocabulary as any declaration does, so a missing file
is then the declaration's configuration error, while the reaction
types alone treat it as empty. Rejected: forbidding declarations to
name `reaction-types`, a special case with no benefit.

**The build stages the labels; the site does not read the file.** The
pipeline writes `build/data/reaction_types.json`, each value mapped to
`{"label": <shown label>}`, the way `fields.json` carries declared
vocabularies with labels already chosen for the site's language. The
existing mount of `build/data` serves it as
`site.Data.collection.reaction_types`, so `site/data/` and its mount
go. Rejected: mounting `vocabularies/` as Hugo data, which would make
the templates choose languages again and expose every vocabulary in
its raw form.

**A starter file in `templates/`, copied by `init`.** The current list
becomes `templates/reaction-types.toml`, so `new` stubs, whose
`reaction_types` is `["esterification"]`, name a value a new collection
has. `init` keeps an existing file, since an interrupted `init` may be
rerun and the file is the collection's. The demo holds the same file;
its procedures already use these slugs.

## Risks / Trade-offs

- [A collection copied from before this change has no reaction types]
  → Every procedure reports `unknown reaction type` naming
  `vocabularies/reaction-types.toml`; copying the template fixes it.
  No user exists, so nothing more is offered.
- [The overlay's mount numbering changes] → The overlay is generated
  and tested as a whole; only the spec's numbering moves.
- [Stricter checks on the file] → The shipped list already meets them.
