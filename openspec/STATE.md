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
