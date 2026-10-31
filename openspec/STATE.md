# State

Work the owner wants that no OpenSpec change covers yet. Each item
becomes a proposal under `openspec/changes/` when it is taken up, and
leaves this file then.

## Wanted features

- **Derived synthesis routes.** On a compound page, the ways to make
  the compound from the collection's procedures: each compound made by
  any procedure that has it among its products (or an entry of a
  general procedure that does), each procedure needing all of its
  substrates, recursively down to compounds no procedure makes.
  Computed at build time, with a depth limit and a guard against
  cycles such as protection and deprotection. Complements the written
  synthesis sequences, which record the route the group actually uses.
- **One PDF per synthesis sequence.** The sequence page prints on its
  own; a single document joining the sequence page and its steps'
  procedures, in order, would need WeasyPrint to render and merge
  several pages.
- **Synthesis sequences written in Org.** Sequences are Markdown only;
  an Org source would need the export to handle `org/sequences/`.
- **Faceted compound directory.** The choice fields a collection
  declares for its compounds become filters on `/compounds/`, through
  a catalogue core whose facets come from the page rather than a fixed
  list, which the procedure catalogue then shares. Selecting a value of
  a hierarchical vocabulary also selects the compounds filed under its
  descendants. The header search on `/compounds/` matches names,
  formulas, CAS numbers, SMILES and the text fields declared
  searchable.
- **Compound tabs.** One declared choice field divides the compound
  directory into tabs: a static page per top-level value of its
  vocabulary, with that value fixed as a term page fixes its term, and
  the lower levels of the hierarchy left as filters within a tab.
- **Procedure fields.** A collection declares custom front-matter
  fields for its procedures, beside those for compounds, with the same
  types and checks; the metadata panel shows them.
- **Reaction types as a collection vocabulary.** The reaction types
  move from the application's `site/data/reaction_types.toml` into the
  collection's vocabularies, so each collection names its own.
- **Compound fields beyond compound views.** A declared compound field
  can be shown where a procedure names the compound, such as an item
  number or a short name beside a product or starting material.
