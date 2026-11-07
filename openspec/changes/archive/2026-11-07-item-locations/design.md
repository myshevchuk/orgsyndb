## Context

`Item` has no location; bulk lots have a free-text `location`. The
item list is a table under a GET filter form, and the lab's pages carry
no scripts. The new delivery note form has ten rows of item choices,
labelled by article number, container and name, and `?item=<id>` fills
the first. The note's page lists its lines with article number, name,
size and count, and the site's `print.css` prints pages.

## Goals / Non-Goals

**Goals:**

- Fach and Box on every item, where staff look for them: the list, the
  item page, the delivery note form and the note itself.
- A request for several articles booked from the list without picking
  each item again.

**Non-Goals:**

- Sorting by location; the item-list table change adds sorting for
  every column, these two included.
- A location vocabulary or validation of the values.
- Recording a line's location on the note when it is booked.

## Decisions

### Two free-text fields

`compartment` and `box`, optional, at most 30 characters, with a
`datalist` of the values in use on the item forms. The freezer's
compartments and boxes are numbered by hand; a vocabulary would need
maintaining before the first item could be entered. The list filters
them by exact value.

### Ticking rows without a script

The check boxes carry `form="pick"`, the id of a separate GET form
above the table whose button, `Lieferschein mit Auswahl`, requests the
new note form. HTML's `form` attribute ties controls to a form outside
which they sit, so the filter form and the selection form never nest,
and no script is needed. Only items with an article number get a box:
the note form offers no other.

The note form reads every `item` parameter in order, drops ids it does
not offer and repeats, and fills the first rows, up to its ten. A
selection of more than ten leaves the rest out.

### The note as pick list

The note's page shows each line's item's compartment and box as they
are now, not as they were when the note was booked: the page is printed
to fetch the containers, which happens at booking time. A historical
note shows the items' present locations, which is what a reprint would
want.

## Risks / Trade-offs

- A selection above ten rows is cut. → Requests rarely exceed ten
  lines; a second note takes the rest.
