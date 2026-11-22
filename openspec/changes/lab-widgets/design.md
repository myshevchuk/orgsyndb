## Context

The lab application's pages link the site's stylesheets (`tokens.css`,
`base.css`, `screen.css`, `print.css`) and then `lab.css`, and load
`lab.js` (web-app "Page shell"). The Hugo site uses the same first
four stylesheets, and WeasyPrint renders procedure PDFs with
`print.css`. Four record pages are to be rebuilt as widgets, one
change each; the procedure page, a Hugo page, comes last. The owner's
chosen mockups live outside the repository, in the operator's
workspace.

The change history is shown by `inventory/history.html` on the item,
batch, vessel and delivery note pages; the task page writes its own
copy of the same list inline, from `tasks/history.py`, whose entries
add a heading per step and a removed step with no changes.

A dialog's save refreshes the page's `[data-refresh][id]` parts with
those of a fresh copy (`refreshParts` in `lab.js`). On the item page
the whole content below the header is one such part. Nothing inside a
part survives the swap today; the item list's view controls survive
because they lie outside its parts.

## Goals / Non-Goals

**Goals:**

- One set of widget classes that both the lab and the Hugo pages can
  use.
- Sorting in the browser, on any table marked `data-sortable`.
- One history widget on every page that shows a history.
- The item page rebuilt from the chosen mockup with its data
  unchanged.

**Non-Goals:**

- The substance, overview, procedure and planning pages, and the rest
  of the batch, vessel, delivery note and task pages: later changes.
- New data, links or figures. The mockups' back-links and the
  compound widget on the item page are left out; the links come in a
  small change of their own.
- Printing through WeasyPrint: no widget appears on a procedure page
  yet, and `print.css` is not touched.

## Decisions

### Widget classes live in the site's `screen.css`

The widget frame, the compact and key–value tables, the figures strip
and the collapsible widget are defined in `site/assets/css/screen.css`,
which both the site and the lab load (media `screen`). `lab.css` holds
only what is lab-specific, such as the item page's grid of two
columns. Rejected: putting them in `lab.css`, which would force the
procedure change to copy them.

Class names: `.widget` on a `section` or `details`, `.widget__head`
(the title bar, the `summary` of a `details`), `.widget__count`,
`.widget__note`, `.widget__body`, `.widget-table` (compact table),
`.kv-table` with `.kv-sub` (muted basis line), `.figures-strip` with
`.figure-tile`. The type inside a widget is 13 px, its tables 12 px,
as in the mockups. The title is an `h2` inside the title bar, so the
pages' heading outline stays (site-theme heading rules).

### Printing opens collapsible widgets by script

Browsers do not print the content of a closed `details`, and pure CSS
cannot open it in every engine. `lab.js` opens every closed
`details.widget` on `beforeprint` and closes those it opened on
`afterprint`. Rejected: rules in `print.css`, which WeasyPrint also
reads and whose warnings fail the print tests (print-layout
"Warning-free rendering").

### One history template, one row per changed field

The task page drops its inline list and includes
`inventory/history.html`. The template becomes a `details.widget`,
closed, titled `Änderungen` with the number of entries, holding a
table with the columns time, user, subject and change. An entry with
several changed fields gives one row per field, its time, user and
subject cells spanning them. A creation's change cell reads
`Angelegt`. The subject is the entry's heading (`Verbrauch Q3 2026`,
`Stufe 2`, `Stufe 2 entfernt`), else empty. An entry without
changed fields shows `Kein Feld geändert` in its change cell, except
an entry with a heading, whose change cell stays empty, as the task
page shows a removed step today.

### Sorting reads `data-sort`, or the cell's text

`lab.js` gains a pure function `sortOrder(keys, descending, locale)`
returning the indices of the rows in their new order, tested under
Node like the script's other pure functions; the collator falls back
to the default locale where Node lacks the language. Key rules are
those of the requirement. Templates give `data-sort` to amounts (the
amount in the base unit), to a date shown with its booking time, and
to any cell mixing a number with a mark.

Activation: a header becomes a button inside the `th`; the first
activation sorts ascending, each further one flips the direction;
activating another column starts it ascending and clears the
previous header's `aria-sort`.

### Refresh carries view state by `id`

Every `details.widget` and every `table[data-sortable]` carries an
`id`. Before `refreshParts` swaps the parts, `refreshPage` records
each one's open state and sort (column index, direction) by `id`;
after the swap, it applies them to the elements of the same `id` and
sorts their new rows. An element without a counterpart is skipped.
Rejected: keeping no state, which would close the history and unsort
the movements on every save in a dialog, against Form dialogs.

### The forecast's sentences are split, not cut

The forecast widget, titled `Prognose`, keeps all it holds today
under that heading, the delivery rhythm included (end-product-inventory
"Item page", production-planning "Item forecast"). Its key–value
table puts each value in bold on the first line of the value cell and
the parameters it used on a `.kv-sub` line under it; the article's
part keeps its `Artikel <number>` sub-heading, and the delivery
rhythm its own. The translated strings are split accordingly and the
German catalogues updated.

### Figures strip

The strip repeats stock (with its `level-<level>` class and label),
coverage, the means per quarter and year, the current year, usable
bulk and latest start, each with the marks it carries where it shows
today: `hochgerechnet aus dem laufenden Jahr` for projected figures,
`grob` for rough ones. A figure the item lacks, such as the latest
start of an item without a forecast, reads `–`. The item's note
moves into the item data widget, the `Neue Charge` link into the bulk
widget.

## Risks / Trade-offs

- [Sorting by text misreads a cell] → `data-sort` on every cell whose
  text is not its value; Node tests cover signs, decimal commas,
  dates with times, `–`, empty keys and German text.
- [A closed history hides a change a user looks for] → its content
  stays in the page, the count shows in the title bar, and print
  opens it.
- [Tests that read the old markup] → listed in tasks; the test writer
  moves them to the new markup in the same change.
- [Site stylesheet grows with lab-only use until the procedure change
  lands] → accepted; the classes are generic and few.
