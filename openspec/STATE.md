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
- **Reagents-table helper in Emacs.** Insert a Reagents row for a
  registry compound, with its name in the procedure's language, CAS and
  MW, and compute mmol and equivalents from a typed amount. Open: the
  density a volume needs, significant figures, decimal commas, the
  reference row, and whether Org tables use spreadsheet formulas.
- **Preview in either language.** The site has one language, `locale`
  in the application's `site/hugo.toml`, so a preview shows the
  variant that suits it. A `serve --locale` option would preview the
  other language's variants without editing that file.
- **Lab records in the web application.** The rest of the concept in
  `ideas/inventory-app.org`, after `task-tracker` and
  `end-product-inventory`: the intermediates, QC, the catalogue's
  properties as compound fields, commercial reagents, Excel import and
  export, and links from the site's navigation to the application.
- **Printing delivery notes.** Once `end-product-inventory` keeps
  delivery notes, the application should print one: its number, date,
  recipient and lines (article number, name, container size, count),
  as a printable page or a PDF through WeasyPrint, so booking a
  delivery and writing its note become one step and no delivery goes
  unrecorded. Open: the layout and letterhead of today's notes,
  whether the application assigns the note numbers, and signatures.
- **Numbers of the database's own.** Article numbers are the
  company's, on delivery notes, and only end products get one, at
  their first delivery; until then an item has none and links to no
  compound or bulk lot. A numbering of the lab's own for every
  synthesized compound would let such items, their lots and tasks link
  before the first delivery. Open: the scheme, whether the registry
  keeps it as a compound field, and how it relates to the article
  number.
- **The mean in an item's second year.** The mean per year divides the
  complete years from the first with data, so an item that entered use
  in, say, October counts that partial year as a whole one, and its
  mean in the next year is far too low. Wanted as a fix for every item:
  count the first year in proportion, from the quarter of its first
  consumption.
- **Handling discontinued items.** An item set to `auslaufend` is
  dormant and left out of planning, but nothing else changes: tasks,
  fillings and syntheses for it are booked as for any other. Open:
  which of these to refuse or warn about, and whether an item may be
  closed once its stock is gone.
- **Heat by category and size.** The item list colours `Ø Jahr` and
  `lfd. Jahr` by the fifth of all consuming items a value falls in, so
  a 5 g size and a 100 mg one, or a reagent and an end product, share
  one scale. Wanted: compare a value within its category or container
  size, or by the amount of substance it stands for. Open: which
  grouping the lab reads, and how small a group may be.
- **The item list's colours on paper.** Browsers print no background
  colours, so the `Bestand`, `Ø Jahr` and `lfd. Jahr` cells keep only
  their text colour. Values in the two darkest heat steps and at level
  `ruhend`, white on screen, print near-white and are hard to read;
  the other values print as dark text whose hue alone hints at their
  level or heat, and nothing on paper names a level. Wanted: values
  that print legibly, with their level and heat. Open: whether paper
  keeps the colours, through `print-color-adjust: exact`, or marks
  level and heat another way, such as a letter beside the value.
- **Planning a new item's first quarter.** The demand models read only
  complete quarters, so an item first delivered in the current quarter
  has no forecast until the quarter ends, though the item list projects
  its means from the current year.
