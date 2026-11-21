## 1. Tests

- [ ] 1.1 The form alone: the filling, correction, consumption, edit
  and reversal forms, requested with `HX-Request`, answer the form
  partial headed by its title, posting with `hx-post` to its own URL,
  without the page shell; requested without, or with
  `HX-History-Restore-Request` too, the complete page as before, whose
  form carries no `hx-post`; all send `Vary` naming both headers
- [ ] 1.2 Errors and refusals in the dialog: an invalid correction, a
  refused filling and the reversal of a movement already reversed,
  posted with `HX-Request`, answer the partial with the errors, the
  last as a form error, and save nothing; `Menge vorschlagen` answers
  the partial with the amount filled in, and with its error when it
  cannot propose
- [ ] 1.3 Saved in a dialog: a valid post with `HX-Request` answers
  204 with `HX-Trigger` `lab-saved` naming the item, books, and leaves
  the message for the next page; without the header it still
  redirects to the item's page
- [ ] 1.4 Signed out: a GET and a POST with `HX-Request`, no user and
  `HX-Current-URL` of the list with `q` and `detail` answer 204 with
  `HX-Redirect` to the sign-in page whose `next` is that whole
  address, and book nothing; signing in with that `next` leads back
  to it; a foreign `HX-Current-URL` gives the form's path; without
  `HX-Request` the redirect is as before; the delivery note and other
  forms are unchanged
- [ ] 1.5 Links: in the list's details and on the item page, the
  links to the four forms and each `Stornieren` carry `data-dialog`,
  `Abgabe buchen` does not; every page has the dialog, its close
  button and an empty body; the list marks its count, summary, stock
  menu, other filters' choices, table body and details, and the item
  page the wrapper holding its heading and actions, each with
  `data-refresh` and an `id`; after a correction posted for a dialog,
  the list requested again shows the row's new count and order and
  the message
- [ ] 1.6 Scripts: the pages still pass web-app "Scripts" (no `on…`
  or `hx-on` attributes)

## 2. Implementation

- [ ] 2.1 `base.html` and `lab.css`: the dialog in the shell
- [ ] 2.2 `form.html`: the `form` partial, with `hx-post` to its own
  URL and `hx-disabled-elt` only for a dialog; the five item views,
  `item_fill`'s `Menge vorschlagen` branch included, render the
  partial for a dialog and answer a save with 204 and `lab-saved`;
  `Vary` on both headers; other forms unchanged
- [ ] 2.3 The sign-in decorator for the five item views
- [ ] 2.4 `item_actions.html` and `item_page.html`: `data-dialog` on
  the links; `data-refresh` wrappers on the item page and the list
- [ ] 2.5 `lab.js`: open on a plain click, close on `Abbrechen`;
  on `lab-saved`, refresh the marked parts and the title, re-tick the
  ticked items, sync the chosen row and `detail`, then close and
  restore focus
- [ ] 2.6 German messages for new strings

## 3. Checks

- [ ] 3.1 Area tests pass: `webapp/tests/test_inventory_*.py`,
  `test_shell.py`, `test_lab_script.py`
- [ ] 3.2 In a browser: open each form from the details and the item
  page; cancel with the button, the close button and Escape; save with
  an error and with `Menge vorschlagen`; save valid. On the list: the
  filters, scroll, chosen item and ticked boxes stay; a correction
  under a stock filter that the item then leaves, with one row left
  and with none, chooses as a reload would and fixes the address; a
  consumption entry recolours other rows as a reload does; a first
  article number turns `Artikelnr. eintragen` into `Abgabe buchen` on
  the item page and in its heading. A form opened in a new tab saves
  as a page. Focus after a save from the pane and from a reversal
  link. Signed out in another tab, opening and saving lead to sign-in
  and back
- [ ] 3.3 On the test server, by the owner
