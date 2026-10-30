## Context

After compound-registry, a procedure names its products and starting
materials by compound key, with a yield per product. A general procedure
is one method applied to several substrates, each run giving its own
products and yields and sometimes needing a longer time, another
temperature or another scale. Sequences, the change after this one,
will name a single run of a general procedure as a step.

## Decisions

- **`scope` makes a procedure general.** No separate `kind` field: a
  procedure with `scope` is general, one without is specific, and the
  site derives the catalogue's `kind` from that. One fact, one place.
- **An entry has the shape of a specific procedure's run.** `substrates`
  and `products` with per-product yields, exactly as at the top level,
  so the validator, the links and the compound pages treat both alike;
  a general procedure's products and substrates are the union over its
  entries. Entries are numbered from 1 in their order, and that number
  is how a compound page and a sequence name one run.
- **Deviations are structured fields.** `scale` (the procedure-level
  rule), `time` (a number and `min`, `h` or `d`), `temperature` (a
  number in °C) and `note`. A table column appears on the page only
  when some entry sets its field.
- **In Org, the scope is a table.** A list of alists on a custom
  front-matter line is unreadable at fifteen entries; an Org table is
  how an Org author writes one anyway. The header row names the keys;
  a cell holds space-separated compound keys or numbers, and an empty
  cell leaves the field unset. The export builds `scope` from it and
  removes it from the body, because the page renders the table from the
  front matter: one source, no copy to drift.
- **Notes are translated, the rest of the scope is shared.** Language
  variants share `scope` as they share `products`, except each entry's
  `note`, which is prose.
- **`products` last within an entry.** tomelr writes keys in order, so a
  key after an entry's `[[scope.products]]` tables would land in the last
  product; the export orders each entry's keys as it orders the top
  level.
- **The scope table sits before the body.** It is the overview of what
  the procedure covers, so it follows the title block and the panel
  and precedes Summary.
- **A scheme image instead of product structures.** Fifteen structure
  figures do not fit a title block; `scheme_image`, an optional
  procedure field with the structure-image path rules, shows the
  general scheme, and a general procedure without one shows the
  placeholder. A specific procedure may set it too, and then shows it
  instead of its product structures.
- **A facet and a fixed view.** The catalogue's `kind` facet makes
  general procedures filterable beside the other facets; the tab leads
  to `/general-procedures/`, a catalogue page with `kind` fixed, built
  like a term page, so that the view works without JavaScript.

## Alternatives rejected

- **A `kind` front-matter field.** It could disagree with the presence
  of `scope`.
- **Free-text conditions per entry.** The owner asked for structured
  deviations; free text cannot be shown in columns or checked.
- **Author-placed scope table (a shortcode where the table stood).** The
  export would rewrite the table into a shortcode and the validator
  would check its placement, for a choice of position that one fixed
  place serves.
- **General procedures as a taxonomy term or as `/procedures/general/`.**
  A taxonomy needs a front-matter value that repeats `scope`; a nested
  section would put a section page among the catalogue's pages.
