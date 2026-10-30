## Context

With compound-registry and general-procedures in place, procedures form
a graph: a procedure turns its substrates into its products, and the
compound pages already show which procedures make and use a compound.
A synthesis is a path through that graph that the group actually runs:
an ordered choice of procedures, and of the entry of a general
procedure, where several would make the same intermediate.

## Decisions

- **A sequence is written, not derived.** A file names the steps in
  order. Which route the group uses, and why, is knowledge the graph
  does not hold; enumerating every route is a separate, later feature.
- **Its own ID space and files.** `SEQ-NNNN`, in the collection's
  `md/sequences/`, as Markdown with TOML front matter: the steps are
  data, the body holds notes such as which intermediate is purified.
  The site mounts the directory as `content/sequences`.
- **Markdown only, with language variants.** A sequence is mostly front
  matter, so it needs no Org export; but the site's default language is
  German, so a sequence has variants by language code, chosen and
  staged as procedures are, sharing their target and steps.
- **Continuity is checked.** Each step after the first starts from a
  product of the step before it, and the target is a product of the
  last step, so a sequence cannot silently break when a procedure
  changes.
- **A step names an entry of a general procedure.** `entry` is required
  for a general procedure and refused for a specific one, so a step is
  always one run with known substrates, products and yields.
- **The overall yield is computed.** It is the product of each step's
  yield of the compound that carries on, which is exact for the data
  the procedures hold, rounded to a whole percent for display.
- **Sequences are not searched.** The catalogue stays a list of
  procedures; a sequence is reached from the navigation, from its
  target's compound page and from the panel of every procedure it uses.

- **No authors.** A sequence records a route through procedures that
  credit their own authors; an `authors` key would also put sequences
  into Hugo's author taxonomy beside the procedures.

## Alternatives rejected

- **Derived routes only.** Shows every possible route, including the
  ones nobody runs, and cannot carry notes.
- **A sequence as a kind of procedure in the catalogue.** It has no
  reagents, scale or single reaction type, so most of the catalogue's
  columns and facets would be empty for it.
- **One combined PDF per sequence.** WeasyPrint would have to render and
  join several pages; the sequence page prints on its own. Left as a
  wanted feature.
