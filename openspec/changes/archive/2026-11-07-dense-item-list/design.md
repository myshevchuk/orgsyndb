## Context

The item list renders on the server: `views.item_list` builds a `Row`
per item with its figures, bulk and compound, filters and sorts them in
Python, and the template writes a table whose second header row holds
the filter controls, bound by `form="filters"` to a form above the
table. The page shell forbids `script` elements. The mockups in the
owner's design folder (`compact.html`) show a denser table, filters
above it, and two popups per row.

## Goals / Non-Goals

**Goals:**

- The mockups' compact layout, popups and stock menu.
- Every view still a URL; sorting and filtering still server-side.
- The page works without the script.

**Non-Goals:**

- The category sidebar of `categories.html`.
- Loading popup content on demand.
- Scripts on any other page.

## Decisions

### Native popovers, placed by the script

Each popup is an element with the HTML `popover` attribute, opened by
a button with `popovertarget`. The browser handles opening and
closing, light dismiss, Escape, focus and the top layer, so no script
is needed for a popup to work; without one, the browser shows it in the
window's centre. `lab.js` listens for `toggle` in the capture phase,
finds the opening button and places the popup below it, or above when
there is no room, kept inside the window. It moves the popup again
while the page or the table box scrolls. The arithmetic is a pure
function, `OrgSynLab.place`, tested under Node like the site's
catalogue core. CSS anchor positioning would need no script but is not
yet in every browser the lab uses.

Each popup sits inside the cell of its button. Then
`tr:has(:popover-open)` marks the row whose popup is open, again
without a script. The popups are rendered with the page, two per item.
For a few hundred items that is a modest page, and it spares an
endpoint and a fetch.

### View choices by CSS, remembered by the script

`Spalten`, `Zeilenhöhe` and `Verbrauch einfärben` are controls outside
every form. `lab.css` reads their state with `main:has(...)` and hides
columns, tightens rows, or drops the heat colours. They therefore work
without a script, but only until the page is left. `lab.js` saves each
control marked `data-remember` to `localStorage` and restores it on
load, so choices survive sorting and filtering. Every cell carries
`col-<key>`, the sort key of its column, or `col-location` for
`Lagerort`.

### Filters above the table

The form `filters` keeps `q`, gains the `category` choice, and owns
the choices `container`, `compartment` and `box`, which sit in the
`Weitere Filter` popup through `form="filters"`. `stock` travels as a
hidden field, and the `Bestandsstatus` menu is a popup of links, each
the list with the filters in force and one level, or none. Choices
marked `data-submit` submit the form on change; the script then hides
`Filtern`. Pressing Enter in the search submits as before. The stock
menu's counts admit every filter but `stock`, so they say what a click
will list.

### Default order

`Item.sort_key` becomes article number, items without one by name,
then `container_order`. The default `sort` becomes `category`, which
sorts by category with ties in that order, the mockup's "Kategorie,
Artikelnr., Gebinde aufsteigend". The line above the table says the
order in those words. Other lists that use `Item.sort_key` see only
the change from unit-then-size to amount, within an article.

### The statistics popup

A pure function turns an item's `Consumption` into the popup's rows:
for each of the two years before the current one and the current year,
the four quarters' totals, the quarters to come empty, and the sum;
the current year's four bars as shares of its largest quarter, the
current quarter marked; and the years whose quarters hold an entered
value above zero.

## Risks / Trade-offs

- [Two popups per row make the page heavier] → Acceptable at the
  lab's size. If it grows, the popups can move to a fragment loaded on
  demand.
- [A view choice flashes its default before the deferred script
  restores it] → The flash is brief, and it only shows a choice that
  differs from the default.
- [`:has()` on `main` re-evaluates styles when a control changes] →
  The rules are few and the controls change rarely.
