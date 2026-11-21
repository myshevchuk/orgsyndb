## Why

Every form in the lab is a page of its own: choosing `Abfüllen` in the
item list's details leaves the list, and saving leads to the item's
page, so the user has to find their way back to the list, its filters
and the item they were working through. The owner decided on
2026-11-18 that the lab's forms open as dialogs over the page they are
chosen from, and on 2026-11-21 that a first change covers the item's
short forms: a save closes the dialog and refreshes what changed in
place, without loading the page anew. The delivery note, with its ten
rows, stays a page; the other forms follow in later changes, on the
same mechanism.

## What Changes

- web-app gains "Form dialogs": how a form chosen on a page shows in a
  dialog over it; how cancelling, errors and a refused booking behave
  there; that a save closes the dialog, shows the message and shows
  the saved record in the page as a reload would, keeping its scroll
  position, chosen item and view controls; that a user no longer
  signed in is led to the sign-in page; and that each such form keeps
  its URL as a complete page.
- end-product-inventory "Inventory forms": on an item's page and in
  the item list's details, the links to the item's edit form, filling,
  count correction and consumption, and on its page the reversal of a
  movement, open those forms in a dialog. `Abgabe buchen` keeps leading
  to the delivery note's form page.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: the shared behaviour of forms shown in a dialog.
- `end-product-inventory`: which of the item's forms open in a dialog.

## Impact

- `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`: the dialog
  every page can show a form in.
- `webapp/orgsyndb_web/static/lab.js` and `lab.css`: opening, closing
  and refreshing.
- `webapp/inventory/views.py`, `templates/inventory/form.html`,
  `item_actions.html`, `item_page.html`, `item_list.html`: the form
  alone for a dialog, the answer to a save, and the parts of the pages
  a save refreshes.
- German messages for any new strings.
- No model, migration or URL changes.
