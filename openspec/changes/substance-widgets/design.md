## Context

`lab-widgets` added the widget classes to the site's `screen.css`, the
history widget and sorting in `lab.js` (web-app "Widgets"), and
rebuilt the item page. The substance page, `registry/substance.html`,
still shows a `dl.metadata`, a lone `figure.structure` and headed
`ul.lab-links` lists whose lines `registry/procedure_item.html`
writes; the route tree, `registry/route_steps.html`, uses the same
line for each step. The owner chose mockup A
(`~/local/workspace/orgsyndb/ui-widgets-survey/mockups/substance-A.html`).

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

The heading line holds the `h1` with the name, then the key in
monospace and the inventory group and chemical classes as small
marks. Below it, a grid of two columns: on the left, a row of the
three widgets `Gebinde`, `Chargen` and `Aufträge`, then `Hergestellt
nach`, `Verwendet in`, `Synthesewege` and `Herstellungswege`; on the
right, the compound widget. Below 60 rem the columns stack, the
compound widget first. The grid lives in `lab.css` under `@media
screen`, as the item page's does, so print keeps block flow.

### Compound widget

A `section.widget` titled `Verbindung` with the key as its note,
holding the `figure.structure` on a white stage and a `.kv-table`
with the rows of the requirement in its order. The name and German
name, which the mockup leaves out, stay as rows: the requirement
names them. The title, rows and order are what the procedure change
repeats.

### Tables instead of middot lines

`Hergestellt nach` has the columns `Vorschrift`, `Eintrag`,
`Ausbeute` and `Status`; `Verwendet in` `Vorschrift` and `Status`;
`Synthesewege` `ID` and `Syntheseweg`; `Gebinde` `Artikel / Gebinde`
and `Bestand`; `Chargen` `Charge` and `Bestand`; `Aufträge` `Auftrag`
and `Status`. An empty cell reads `–`. Each title bar shows the
number of rows. The route tree keeps `procedure_item.html`'s line, a
tree's step being no table row.

### Herstellungswege collapsible, open

The tree is the longest part of the page. It sits in a
`details.widget` with an `id`, open when the page loads, so that it
reads as today and can be folded away; its state survives a refresh
as every collapsible widget's does.

## Risks / Trade-offs

- [The compound widget is written twice, in Django and later in
  Hugo] → its rows and order are fixed here and the procedure change
  copies them; a test there compares the two.
- [Tests read the old lists] → listed in tasks; moved to the widgets.
