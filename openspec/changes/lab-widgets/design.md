## Context

The lab application's pages link the site's stylesheets (`tokens.css`,
`base.css`, `screen.css`, `print.css`) and then `lab.css`, and load
`lab.js` (web-app "Page shell"). The Hugo site uses the same first
four stylesheets. Four record pages are to be rebuilt as widgets, one
change each; the procedure page, a Hugo page, comes last. The owner's
chosen mockups live outside the repository, in the operator's
workspace.

The change history is one template, `inventory/history.html`, that
the item, batch, vessel, delivery note and task pages include.

## Goals / Non-Goals

**Goals:**

- One set of widget classes that both the lab and the Hugo pages can
  use.
- Sorting in the browser that needs no markup beyond `data-sortable`
  and works on any table of the lab.
- The item page rebuilt from the chosen mockup with its data
  unchanged.

**Non-Goals:**

- The substance, overview, procedure and planning pages: later
  changes.
- New data, links or figures on any page. The mockups' back-links and
  the compound widget on the item page are left out.
- Server-side sorting of the item list, which stays as it is.

## Decisions

### Widget classes live in the site's `screen.css`

The widget frame, the compact and key–value tables, the figures strip
and the collapsible widget are defined in `site/assets/css/screen.css`,
which both the site and the lab load. `lab.css` holds only what is
lab-specific, such as the item page's grid of two columns. Putting
them in `lab.css` would force the procedure change to copy them.

Class names: `.widget`, `.widget__head` (title bar), `.widget__count`,
`.widget__note`, `.widget__body`, `.widget-table` (compact table),
`.kv-table` with `.kv-sub` (muted basis line), `.figures-strip` with
`.figure-tile`, and `details.widget` for the collapsible widget. The
type inside a widget is 13 px, its tables 12 px, as in the mockups.

### History rows: one per changed field

The history table has the columns time, user, subject and change. An
entry with several changed fields gives one row per field; its time,
user and subject cells span those rows. A creation gives one row
reading `Angelegt`. The subject is the entry's heading where it has
one (entered consumption, `Verbrauch Q3 2026`) and otherwise empty.
The widget is closed by default.

### Sorting reads the cell's text, or `data-sort`

`lab.js` gains a pure function that, given the rows' keys, the column
and the direction, returns the new order. A cell's key is its
`data-sort` attribute when it has one, otherwise its text. A key
parses as a number when it reads as one with a decimal comma or point,
an optional unit after it; as a date when it reads `DD.MM.YYYY` or
ISO; otherwise it compares with `Intl.Collator` in the page's
language. Templates set `data-sort` where the text would mislead, such
as a date shown with its booking time. The pure function is tested
under Node like the script's other pure functions.

The sort state is held on the table (`aria-sort` on the header) and,
on refresh after a dialog, re-applied to the new table by the same
code that keeps the item list's view controls.

### The forecast's sentences are split, not cut

Each forecast value keeps every figure and parameter it names today
(production-planning "Item forecast": each figure names the
parameters it used). The value moves into the key cell's first line,
in bold; the parameters move to a `.kv-sub` line under it. The
translated strings are split accordingly and the German catalogue
updated.

## Risks / Trade-offs

- [Sorting by text misreads a cell] → `data-sort` on any cell whose
  text is not its value; the Node tests cover numbers with units,
  dates, `–` and German text.
- [A collapsed history hides a change a test or a user looks for] →
  the content stays in the page (`details`), and print opens it.
- [Site stylesheet grows with lab-only use until the procedure change
  lands] → accepted; the classes are generic and few.
