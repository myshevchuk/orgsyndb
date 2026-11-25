## Context

The item list already has the two views, the selection by
`selected=<id>`, details loaded in place by htmx and the cookie of the
view; the frame of `bestand-frame` gives every Bestand list its fixed
height. The approved reference is `widget-mockups-2/01`–`03`.

## Decisions

- **Layers as links, not a new page.** The three layers stay three
  pages at their own addresses; the layer switch is a segmented group
  of links at the left of the toolbar, each with its count. Old
  addresses do not change, so the delivery list and its links keep
  working.
- **One selection mechanism.** The bulk and delivery lists reuse the
  item list's script and markup for rows, selection, the view switch
  and in-place details, generalised where it names the item list
  (cookie name, details URL); each list's details come from a
  fragment view answering htmx requests, as `item_detail` does.
- **Reicht für** is computed per vessel and item with the existing
  conversion of Filling from bulk (`figures`), the same numbers the
  item details sum.
- **Tabs.** `Alle Gefäße` stands apart at the right of the tab row, as
  in the mockups; that is layout, not spec.
- **Counts** in the layer switch are computed on every request of the
  three lists: items, bulk vessels without filters, delivery notes.

## Risks / Trade-offs

- Generalising the item list's script risks regressions there; its
  tests cover selection, the view cookie and the details.
