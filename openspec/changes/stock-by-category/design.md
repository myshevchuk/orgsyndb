## Context

The Bestand frame (`bestand-frame`) fits the lists to the window and
lets only their tables scroll; the item, bulk and delivery lists share
one selection mechanism (`.item-layout` with `data-cookie`, rows with
`data-item` and `hx-get`, the pane `#item-detail`). Vessels record
`opened_on` (`vessel-opened-on`). The approved references are
`widget-mockups-2/04`–`08` in the owner's workspace; the brainstorm
behind them is `astra-2.md` and `neon-2.md` there.

## Goals / Non-Goals

Goals: two lists by substance with summaries that do not mislead, the
selected substance's vessels in a full-width table with their actions,
the same frame, toolbar and view switch as the other Bestand lists.

Non-goals: `Verwendet in` (which procedures use an intermediate),
purity, expiry, hazards, supplier documents, a stored category, volume
units, changes to Endprodukte or Chargen.

## Decisions

- **Category derived, not stored.** The category follows from the
  article and the batch's source on every read, so giving a substance
  an article moves its vessels without a migration. A function on the
  vessel (`category`) and one query filter per category express it;
  the vessel kind keeps `Kolben` as its own value for the vessel list,
  where a flask is a kind but not a category.
- **Summaries in a pure module.** The row cells (amount by unit, counts,
  first location `+n`, tasks, suppliers, earliest opening, ages) are
  computed by pure functions over vessel records, tested without the
  database; the views only gather vessels and pass them in. Ages count
  whole calendar months, with `<n> Tage` below one month.
- **Filters act on vessels.** `q`, `location`, `flask`, `old`,
  `supplier` and `sealed` admit vessels; `class` and `group` admit
  substances. A row's cells summarise its admitted vessels, so a filter
  never shows an amount it hid. The page's offered values come from the
  category's open vessels, not from the filtered set, so a filter can be
  changed without clearing the others.
- **Selection by key.** Rows are substances, selected by
  `selected=<key>` and loaded in place from
  `/lab/inventory/intermediates/<key>/` and
  `/lab/inventory/chemicals/<key>/` for htmx requests, as the item
  list's details are; other requests redirect to the list.
- **Vertical split in `Details`.** The table above and the vessels
  below share the frame's height at a fixed ratio of about 45 to 55,
  each scrolling in its own box with a sticky head; the ratio does not
  follow the selection, so arrowing through substances never moves the
  divider. `.item-layout` takes a modifier for this orientation; the
  selection script is unchanged.
- **Actions in dialogs.** The vessel withdrawal, transfer and
  correction forms become dialog forms (as the item forms are); after a
  save the list's parts marked for refresh are replaced, so the row's
  sums and the vessel table show the new amounts.
- **Wareneingang** is the new-batch form with the substance and the
  source `gekauft` filled in; no separate receipt form.

## Alternatives rejected

- **Grey substance header rows over vessel rows** (series 1): read as
  section labels and move the focus to vessels; rejected by the owner.
- **Vessels in the right-hand details pane**: too narrow for a vessel
  table of five or more bottles.
- **Expandable subrows**: two entity types in one keyboard order, rows
  jumping, column grids that do not match.
- **Count popovers**: pointer-only, clip at the viewport edge.
- **A `Substanz | Gefäß` switch**: a second view switch beside
  `Tabelle | Details`; `Alle Gefäße` already lists vessels.
- **Drill-in to a full-height vessel table** (mockup 09): more room for
  ten bottles, but comparing substances needs a round trip; the owner
  chose the split.
- **Summing to one unit** (mg into g, µmol into mmol): kept by unit, as
  the batch list shows amounts, so no figure is converted silently.
- **Keeping `Reagenz`** as the vessel kind: two names for one category
  in one section.

## Risks / Trade-offs

- Computing summaries in Python per request is linear in the open
  vessels; at hundreds of vessels this is negligible, and the lists are
  not paginated, as the other Bestand lists are not.
- Making the vessel forms dialog forms changes how they answer a
  dialog request; their page form stays as it is.
