## 1. Tests

- [ ] 1.1 The form alone: the filling, correction, consumption, edit
  and reversal forms, requested with `HX-Request`, answer the form
  partial headed by its title, posting to its own URL, without the
  page shell; requested without, the complete page as before; both
  send `Vary: HX-Request`
- [ ] 1.2 Errors and refusals in the dialog: an invalid correction and
  a refused filling, posted with `HX-Request`, answer the partial with
  the errors and save nothing; `Menge vorschlagen` answers the
  partial with the amount filled in
- [ ] 1.3 Saved in a dialog: a valid post with `HX-Request` answers
  204 with `HX-Trigger` `lab-saved` naming the item, books, and leaves
  the message for the next page; without the header it still
  redirects to the item's page
- [ ] 1.4 Signed out: a request with `HX-Request` and no user answers
  `HX-Redirect` to the sign-in page with `next` the page's address
- [ ] 1.5 Links: in the list's details and on the item page, the
  links to the four forms and each `Stornieren` carry `data-dialog`,
  `Abgabe buchen` does not; every page has the dialog, its close
  button and an empty body; the item page and the list mark their
  refreshed parts with `data-refresh` and an `id`
- [ ] 1.6 Scripts: the pages still pass web-app "Scripts" (no `on…`
  or `hx-on` attributes)

## 2. Implementation

- [ ] 2.1 `base.html` and `lab.css`: the dialog in the shell
- [ ] 2.2 `form.html`: the `form` partial, `hx-post` to its own URL,
  `hx-disabled-elt`; `form_page` and `saved` for htmx requests;
  `Vary: HX-Request`
- [ ] 2.3 Sign-in redirect for htmx requests
- [ ] 2.4 `item_actions.html` and `item_page.html`: `data-dialog` on
  the links; `data-refresh` wrappers on the item page and the list
- [ ] 2.5 `lab.js`: open on a plain click, close on `Abbrechen`,
  refresh on `lab-saved`, keeping the row's state
- [ ] 2.6 German messages for new strings

## 3. Checks

- [ ] 3.1 Area tests pass: `webapp/tests/test_inventory_*.py`,
  `test_shell.py`, `test_lab_script.py`
- [ ] 3.2 In a browser: open each form from the details and the item
  page, cancel with the button and Escape, save with an error, save
  valid; the list keeps its filters, scroll, chosen item and ticked
  boxes, and the row, pane and counts show the new state
- [ ] 3.3 On the test server, by the owner
