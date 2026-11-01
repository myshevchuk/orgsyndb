## Context

Every `a.compound` the site writes comes from one partial,
`site/layouts/_partials/compound-link.html`, called by the metadata panel
(`procedure-meta.html`, products and starting materials), the scope table
(`scope-table.html`), the sequence scheme (`sequence-compound.html`) and
the sequence directory (`sequences/section.html`). The registry's entries,
declared values included, are `site.Data.compounds`; the field data is
`site.Data.collection.fields.compound`; `field-value.html` writes a value
as the compound page does. The validator's per-type options live in
`TYPE_OPTIONS`, and the options a procedure field withholds in
`PROCEDURE_WITHHELD_OPTIONS` (`tools/validate.py`).

## Goals / Non-Goals

**Goals:** let a collection choose compound fields whose values travel
with the compound's name wherever the site links it.

**Non-Goals:** the note in plain-text names (the key facts' yields, the
catalogue's details view, an image's `alt`, a page title); labels for
the noted values; a per-place choice of fields.

## Decisions

- **One option on the declaration, `beside`.** The collection decides
  per field, as it does with `column`. Rejected: a list of keys at the
  top of `orgsyndb.toml`, which would split one field's settings over
  two places; a fixed choice such as "every `unique` text field", which
  guesses at intent.
- **`text` and `number` only.** These hold identifiers and short names,
  readable without their label. A bare `Yes`, or a class such as
  `Esters`, beside a name says nothing until labelled, and a label would
  turn a short note into a phrase. Rejected: all four types with labels.
- **Every `a.compound`, through `compound-link.html`.** One rule for every
  link reads the same on a procedure, a scope table and a sequence, and
  costs one partial. Rejected: the metadata panel alone, which would
  leave a general procedure's scope table and the sequence pages without
  the values the panel shows.
- **After the link, outside it.** The link's text stays the compound's
  shown name, which existing tests, link text for assistive technology
  and the plain-text names elsewhere all rely on. The note is one
  `span.compound-beside`, written after a space: `(`, the values in
  declared order joined by `, `, `)`.
- **Muted colour.** `base.css` writes the note in `var(--muted)`, whose
  contrast against `--bg` and `--surface` the theme already checks in
  both schemes; print sets `--muted` to black.
- **No label in the markup.** A `title` attribute per value would show
  only on hover and adds nothing the compound page does not hold.

## Risks / Trade-offs

- Long notes crowd a list of starting materials. The collection chooses
  which fields go beside a name, and only `text` and `number` qualify.
- A number field beside a name, such as a stock in grams, reads without
  its label. The unit travels with it; the choice stays the
  collection's.
