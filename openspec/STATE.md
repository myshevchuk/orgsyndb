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
- **Cross-references in procedure bodies.** Body text names procedures
  and compounds as plain text, such as "the product of OSDB-0004".
  Markdown links `[](compound:<key>)` and `[](procedure:OSDB-NNNN)`, and
  Org link types `[[compound:<key>]]` and `[[procedure:OSDB-NNNN]]`
  exported to the same Markdown, would let a Hugo render hook link the
  target and fill an empty link text with its name, and let the
  validator report unknown targets. Still open: whether a mention also
  relates the two pages, such as a "Mentioned in" list. Editor
  completion of these links waits on them.
- **Preview in either language.** The site has one language, `locale`
  in the application's `site/hugo.toml`, so a preview shows the
  variant that suits it. A `serve --locale` option would preview the
  other language's variants without editing that file.
