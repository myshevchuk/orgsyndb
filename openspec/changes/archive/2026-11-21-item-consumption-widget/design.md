## Context

`EnteredConsumption` (`webapp/inventory/models.py`) holds one value
per item and quarter and has no history; the other inventory models
keep one through `RecordedHistory`, and bookings name the author with
`_attributed(record, user)` before a save. `enter_consumption`
(`bookings.py`) replaces a value with `update_or_create` and removes
one with a queryset `delete()`, which writes no history record.

The item page (`item_page.html`) renders the consumption chart and the
table of quarters inline from `item_page`'s context (`chart`,
`quarters`). The consumption form renders the shared
`inventory/form.html`, which since `item-form-dialogs` opens in the
lab's dialog from the item list's details and the item page. The task
page already merges its steps' history into the task's under a heading
per step (`tasks/history.py`).

## Goals / Non-Goals

**Goals:**
- One consumption section, the chart and the table of quarters, that
  the item page and the consumption form both render, with a link per
  quarter.
- The form opened for a quarter shows and names its stored value.
- Entered consumption with a history, shown in the item's history.

**Non-Goals:**
- Links in the item list's details, whose compact table stays as it is.
- Moving past consumption into a maintenance section (STATE.md).
- Any change to how consumption is computed, or to the rule about
  historical notes.

## Decisions

**The consumption section as a template of its own.**
`inventory/consumption.html` renders the chart and the table of
quarters from a context that one function builds, `consumption(item,
today, links)`, named `consumption_section` so as not to shadow the
`consumption` figures function `views.py` imports and the item list
uses, called by `item_page` and `item_consumption`. A stored zero is a
value: its quarter links `Ändern` and fills in 0; only a quarter without
a record links `Nachtragen`. The chart's title takes an `id` per
rendered copy, since the dialog opened over the item page shows a
second one. Each row of
the table carries the quarter's link when `links` asks for them, the
item has an article number and the quarter takes a value; a quarter
takes one when it has begun and holds no line of a historical note
that is not reversed, the test `enter_consumption` makes, factored
into a function both use. On the item page the links carry
`data-dialog`, so they open the form in the dialog. In the form, the
links lead to the form for their quarter: in the dialog they carry
`hx-get` with the dialog's body as target, since the page's handler
opens no second dialog over an open one; as a page they are plain
links. While the dialog's form is posted and the page refreshed after
a save, `lab.js` makes the dialog's body inert, so no quarter link can
replace the form whose save is under way and `lab-saved` still finds
its form in the dialog. Considered: a section for the form only, with the item page
keeping its own. Rejected: the owner asked for one interface in both
places.

**The consumption form's template.** The form gets a template of its
own that extends `inventory/form.html`'s structure: its `form`
partial, used for the dialog, holds the fields and, beside them, the
consumption section, so that the dialog and the page show the same.
`form.html` itself is not made to know about consumption.

**The form for a quarter.** `item_consumption` reads `year` and
`quarter` from the query; when both are valid and name a quarter that
has begun, the form is fixed to that quarter: the year and quarter are
hidden fields, the form names the quarter as text, its count starts at
the stored value, and the value a save replaces is named beside it.
The fixed form posts to the same URL with its query, so a form shown
again with errors stays fixed and keeps naming the stored value. Other
values are ignored and the form opens as today, with editable fields
and no value named; that form is the way to quarters older than the
table shows. Considered: keeping the fields editable and naming the
loaded quarter's value. Rejected: changing the fields would leave the
notice naming another quarter's value than the one a save replaces.
Considered: reloading the form when its year or quarter changes.
Rejected: it would discard a count already typed.

**History.** `EnteredConsumption` gains `history = RecordedHistory()`
and a migration creating its history table. The committed table
diagram `webapp/docs/database-schema.html` is regenerated, and the
history tables its test expects gain the new one. `enter_consumption`
attributes the save to the user, and removes a value by deleting the
instance after attributing it, so the removal is recorded with its
author. A data migration writes one creation record for each value
already stored, with `history_user` its `entered_by` and
`history_date` its `entered_at`, so that a later change has a record
to compare with.

**The item's history.** `history_entries(item)` merges the records of
the item's entered consumption, as `tasks/history.py` merges a task's
steps: an `Entry` gains a `heading`, `Verbrauch Q<quarter> <year>`
for consumption records and empty for the item's; a creation lists
the count from `–`, a change from its old to its new count, a removal
to `–`. Changes are computed per source in `history_id` order, each
consumption record against the previous one of the same item, year
and quarter, which includes records whose live row is gone; the
entries are then shown by descending `(history_date, source,
history_id)`, the consumption's source ranking above the item's, as
the task's history ranks its steps. `history.html` shows a heading when
an entry has one. Lots and delivery notes keep their history as it is.

## Risks / Trade-offs

- The dialog grows with the chart and table beside the fields. → The
  dialog's width allows the table; on a narrow screen the section
  follows the fields.
- Values replaced before this change leave no trace of their earlier
  counts. → The history starts with their current values; nothing
  older exists to restore.
