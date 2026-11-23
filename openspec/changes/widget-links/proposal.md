## Why

The widget survey found links that the redesigned pages still miss: a
record page has no way back to its list but the navigation, the lab
overview names a delivery note without a number as `–`, its latest
notes have no way to the full list, a procedure's lab-notebook value is
plain text although the lab has a page for each notebook, and the home
page links the overview twice, once inside the framed summary and once
under it. The owner asked for these as one small change after the
widget pages.

## What Changes

- Seven record pages — item, batch, vessel, delivery note, task,
  substance and notebook — begin with a back link `← <list>` to their
  list. The notebook page's plain link becomes that back link.
- `Letzte Lieferscheine` on `/lab/` names a note without a number
  `#<id>`, as the note's own page does, and its title bar links
  `Alle →` to the delivery list.
- A procedure page's `Laborjournal` value links to the lab's notebook
  page `/lab/journal/<code>/`.
- The framed summary `/lab/summary/` drops its own `Zur Übersicht`
  link; the home page keeps `Laborübersicht öffnen` under the frame.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: new requirement "Back links".
- `lab-overview`: "Overview page" (`#<id>`, `Alle →`) and "Summary for
  the home page" (no own link to `/lab/`).
- `site-theme`: "Metadata panel" (the notebook value links its page).

## Impact

- Templates: `inventory/item_page.html`, `batch_page.html`,
  `vessel_page.html`, `note_page.html`, `tasks/page.html`,
  `registry/substance.html`, `journal/notebook.html`, a shared partial
  for the back link, `overview/overview.html`, `overview/summary.html`;
  `site/layouts/_partials/procedure-meta.html`.
- `lab.css` for `.lab-back`; German catalogues where a string is new.
- Tests reading the summary's link (`test_overview.py`,
  `test_widgets_overview.py`) and the overview's `–` for notes.
