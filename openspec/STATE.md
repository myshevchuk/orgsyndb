# State

Work the owner wants that no OpenSpec change covers yet. Each item
becomes a proposal under `openspec/changes/` when it is taken up, and
leaves this file then.

## Wanted features

- **One PDF per synthesis sequence.** The sequence page prints on its
  own; a single document joining the sequence page and its steps'
  procedures, in order, would need WeasyPrint to render and merge
  several pages.
- **Synthesis sequences written in Org.** Sequences are Markdown only;
  an Org source would need the export to handle `org/sequences/`.
