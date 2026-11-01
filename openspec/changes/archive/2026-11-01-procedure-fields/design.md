## Context

Compound fields (`compound-fields`) give a collection typed,
validated fields declared in `orgsyndb.toml`, shown on compound pages,
filterable in the compound catalogue, and backed by hierarchical
vocabularies. Procedures carry TOML front matter, written directly in
Markdown sources or emitted by ox-hugo from Org sources, and the
validator warns about every key outside the schema. The procedure
catalogue already reads its facets and row values from the page, so a
facet the page renders needs no script change.

## Goals / Non-Goals

**Goals:**
- Procedures take declared fields with the compound fields' types,
  options, vocabularies and messages.
- The metadata panel shows them; the procedure catalogues filter by
  those declared as facets; the catalogue search finds their values.
- Org and Markdown sources set them alike.

**Non-Goals:**
- Declared fields as procedure table columns or in the Details view.
- Tabs by a procedure field.
- Declared fields in the stubs `new` writes.
- Reaction types as a collection vocabulary, and compound fields shown
  on procedure pages: separate items of `openspec/STATE.md`.

## Decisions

**A capability of its own that refers to `compound-fields`.** The
types, vocabularies, value checks and display rules are written once,
in `compound-fields`; `procedure-fields` states what differs: the
table name, the options a procedure field does not take, the reserved
keys, how uniqueness and variants work, and where the site shows the
values. Rejected: renaming `compound-fields` to a collection-wide
capability, which would rewrite every living reference to it for no
change in behaviour; and copying the shared rules into a second
capability, which would let the two drift.

**No `column`, `search` or `tabs`.** The procedure table's columns are
fixed and already wide. The catalogue search runs on Pagefind's index,
which holds the metadata panel, so every shown value is found without
an option. The procedure section has its own tabs (`All procedures`,
`General procedures`, `Reaction types`, `Tags`, `Authors`), and a
second row of tabs would compete with them. Each of these can be added later as an option
without changing the declarations already written.

**Every procedure, general ones included.** A declared field describes
a procedure as a record of the group (notebook, project, effort), which
applies to a general procedure as well. A collection that wants a field
only on specific procedures leaves it optional.

**Variants share every declared value.** A declared value is a fact of
the procedure, not of its prose; only the field's label is translated,
and that comes from the settings file. Sharing follows the existing
variant check, so a translation that disagrees is an error under the
field's key, naming the reference variant. Rejected: letting text
fields differ between languages, which would make `unique` and the
facets depend on the language of the published variant.

**Uniqueness per procedure.** Variants of one ID share the value, so
`unique` compares the procedures that stand for their IDs (the
reference variants) and names the other procedures by ID, as the
compound check names other compounds by key.

**Reserved keys.** A procedure field key must not be a key the
procedure schema gives a meaning to, a front-matter key Hugo reads for
itself (its value would steer the page instead of reaching `.Params`
as data), or a record key or address parameter of the procedure
catalogue. The list is written out in the requirement so that tests
and messages agree with it. A compound field and a procedure field may
share a key: the two never meet in one file or one catalogue.

**Placement.** In the metadata panel the declared fields follow the
people (`Authors`, `Checked by`) and precede the dates, so the facts of
the procedure come before its history and links. In the procedure
catalogue the declared facets follow `Status` and precede `Tag` and
`Author`, whose long lists close the column; they carry `open`, as the
compound catalogue's do.

**A demo without required procedure fields.** The demo declares a
field of every type and every sample sets `notebook` and `project`,
but none is `required`. The site tests add fixture procedures, Org and
Markdown, to a copy of the test collection, and the build validates
before Hugo runs; a required field would have to be written into every
added fixture. The validator fixture covers `required` for procedures.

**Org values as ox-hugo types them.** An Org source sets a declared
field on a `#+HUGO_CUSTOM_FRONT_MATTER:` line, which the export already
passes through. ox-hugo writes a value that looks like an integer or a
boolean without quotes, even when the source quotes it: tomelr, which
writes the front matter, coerces every string that reads `true` or
`false`, looks like an RFC 3339 date, or is a fixnum integer, list
entries included. `"1234"` becomes `1234`, `"true"` becomes `true`,
`"2026-01-01"` a TOML date, and `"0012"` becomes `0012`, which is not
valid TOML. A text or choice value of such a form therefore cannot come
from an Org source; the validator reports its type, or the export's
front matter fails to parse. Rejected: turning tomelr's coercion off
during the export, since ox-hugo itself relies on it (it writes
`draft = false` from the string `"false"`), and Org authors would lose
their way to write booleans.

## Risks / Trade-offs

- [A required procedure field makes every stub `new` writes fail
  validation until it is filled] → The stub already names the
  placeholder compound `example-compound`, which a real collection
  lacks; the author fills both.
- [A reserved-key list ties the validator to Hugo's front-matter keys]
  → The list names the front-matter keys of current Hugo releases; a
  key a later release adds would show up in the built pages, not in
  the validator.
- [The facets column grows with each declared facet] → Declared facets
  are the collection's choice, and the narrow-window toggle already
  hides the column.
