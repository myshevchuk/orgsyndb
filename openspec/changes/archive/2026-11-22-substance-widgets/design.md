## Context

`lab-widgets` added the widget classes to the site's `screen.css`, the
history widget and sorting in `lab.js` (web-app "Widgets"), and
rebuilt the item page. The substance page, `registry/substance.html`,
still shows a `dl.metadata`, a lone `figure.structure` and headed
`ul.lab-links` lists whose lines `registry/procedure_item.html`
writes; the route tree, `registry/route_steps.html`, uses the same
line for each step. The owner chose mockup A of
the UI survey, kept outside the repository; this design states what
the change takes from it.

## Goals / Non-Goals

**Goals:**

- The substance page as mockup A, from the widget classes already in
  place, with the data it shows today and nothing more.
- A compound widget whose markup the procedure change can repeat in
  Hugo, so that the same data looks the same on both pages.

**Non-Goals:**

- The substance list `/lab/registry/` and the vocabulary pages.
- The mockup's back-link `← Substanzen` (the later links change) and
  its total of containers in the `Gebinde` title bar, a figure the
  page does not show today.
- Sorting: the page's tables are short, and their sizes and amounts
  mix units that no single key orders.

## Decisions

### Layout

The heading line holds the `h1` with the name, then, as in the
mockup, the key in monospace and the inventory group and chemical
classes as small marks; the spec does not require them, the compound
widget holds the same values. Below it, a grid of two columns: on the left, a row of the
three widgets `Gebinde`, `Chargen` and `Aufträge`, then `Hergestellt
nach`, `Verwendet in`, `Synthesewege` and `Herstellungswege`; on the
right, the compound widget. Below 60 rem the columns stack, the
compound widget first. The grid lives in `lab.css` under `@media
screen`, as the item page's does, so print keeps block flow.

### Compound widget

A `section.widget` titled `Verbindung` (`Compound`) with the key as
its note, holding the `figure.structure` and a `.kv-table` with the
rows article number, formula, molar mass, CAS number, SMILES with its
copy button, inventory group (linking `/lab/registry/groups/`),
chemical classes, key, name, German name, short name and note. The
order follows the mockup; the spec names the data, not the order. The
name and German name, which the mockup leaves out, stay: the
requirement names them.

The figure stands on the page background, not on a white stage, so
that the dark scheme's inversion of `.structure img` (`screen.css`)
keeps the drawing visible. The widget's own rules, such as the
figure's size inside it, go into `site/assets/css/screen.css` beside
the other widget classes, so that the procedure page can use them;
`lab.css`'s rule `main > .structure`, which no page needs once the
figure moves, goes.

### Tables instead of middot lines

Column labels, German (English): `Hergestellt nach` has `Vorschrift`
(`Procedure`), `Eintrag` (`Entry`), `Ausbeute` (`Yield`) and `Status`
(`Status`); `Verwendet in` `Vorschrift` and `Status`; `Synthesewege`
`Syntheseweg` (`Sequence`), one cell holding the link `<ID> <title>`;
`Gebinde` `Artikel / Gebinde` (`Article / size`) and `Bestand`
(`Stock`), the latter `<n> Gebinde`; `Chargen` `Charge` (`Batch`) and
`Bestand`; `Aufträge` `Auftrag` (`Task`) and `Status`. An empty cell
reads `–`. A title bar shows the number of rows when there is at
least one; an empty widget has no count and reads `Keine`. The route tree keeps `procedure_item.html`'s line, a
tree's step being no table row.

### Herstellungswege collapsible, open

The tree is the longest part of the page. It sits in a
`details.widget` with an `id`, open when the page loads, so that it
reads as today and can be folded away.

## Risks / Trade-offs

- [The compound widget is written twice, in Django and later in
  Hugo] → its rows and order are fixed here and the procedure change
  copies them; a test there compares the two.
- [Tests read the old lists] → listed in tasks; moved to the widgets.
