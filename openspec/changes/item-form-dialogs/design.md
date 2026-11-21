## Context

The lab loads htmx 2.0.11 and `lab.js` on every page, with
`allowEval` off and no inline scripts or `on…` attributes (web-app
"Scripts"). Django 6.0's template partials already give the item list
its details pane (`item_list.html#detail`). Every inventory form
renders `inventory/form.html` through `form_page`, and a save goes
through `saved`, which stores a message and redirects to the item's
page. Messages show from `base.html` in a `ul.lab-messages` at the top
of `main`.

## Goals / Non-Goals

**Goals:**
- One dialog mechanism the later changes reuse for the other forms.
- The item's short forms in a dialog from the item list's details and
  the item page, with errors, a refused booking and `Menge vorschlagen`
  handled inside the dialog.
- After a save, the changed parts of the page refreshed in place,
  leaving the list's filters, scroll position, chosen item, ticked
  check boxes and view controls alone.

**Non-Goals:**
- The delivery note forms, new item, the bulk lot forms, tasks,
  registry and account forms.
- Sorting or filtering through htmx.
- A message in the details pane when loading fails (STATE.md).

## Decisions

**One `dialog` in the shell.** `base.html` holds one
`<dialog id="lab-dialog">` after `main`, with a close button and an
empty body. A link opens its form in it when it carries
`data-dialog`; it stays a plain link with its `href`, so a modified
click, a new tab or no script open the form page. `lab.js` takes a
plain click on such a link, asks htmx for the `href` into the
dialog's body, and calls `showModal()` once the form has been swapped
in. Marking links with a data attribute rather than `hx-get` keeps
the decision of when to open a dialog (plain click only) in one
place and leaves the links' markup unchanged otherwise.

Considered: a dialog per form rendered into each page. Rejected: the
item list would carry every item's forms, as the removed popups did.

**The form alone for htmx.** `form.html` wraps its heading and form
in a partial (`{% partialdef form inline %}`), the heading an `h2` in
the partial and the page's `h1` outside it. `form_page` renders
`inventory/form.html#form` when the request carries `HX-Request` and
is not a history restore, and the whole page otherwise, and its views
send `Vary: HX-Request`. The partial's form posts with `hx-post` to
its own URL (an explicit `action`, so the dialog does not post to the
page behind it) and swaps its answer into the dialog's body, which
gives errors, a refused booking and `Menge vorschlagen` with no
further code. Its `Abbrechen` stays a link to the cancel URL;
`lab.js` closes the dialog on a plain click on it.

**The answer to a save.** `saved` stores the message as now. For an
htmx request it answers `204 No Content` with
`HX-Trigger: {"lab-saved": {"item": <id>}}` instead of the redirect;
htmx swaps nothing on a 204 and still fires the event. Any other
request is redirected as before.

**Refreshing in place.** On `lab-saved`, `lab.js` closes the dialog,
fetches the page's own address with `HX-Request` absent, parses the
answer, and replaces by `id` each element of the page marked
`data-refresh`, then the item's row (`tr[data-item="<id>"]`) when the
page has one, and the messages; it calls `htmx.process` on what it put
in. The message is consumed by that fetch, so it shows exactly once.
What the page marks:
- the item page: one wrapper around everything below its heading and
  actions;
- the item list: the details pane (`#item-detail`), the stock filter
  menu with its counts, and the heading's count. The rows are not
  marked as a whole, so the other rows' ticked check boxes stay; the
  saved item's row is replaced and keeps its `aria-current`,
  `tabindex` and check box state from the row it replaces.

When the saved item no longer matches the list's filters, the fetched
page has no such row and the details of its first item: the row is
removed and the pane follows, as a reload would show.

Considered: an out-of-band swap rendered by the save itself. Rejected:
the save would need to know which page it was opened from and render
that page's parts; the fetch keeps every view rendering only itself.
Considered: replacing `main`. Rejected: it would reset the view
controls and the list's ticked check boxes.

**Signed out meanwhile.** `login_required` redirects to the sign-in
page and the browser follows it, so htmx would show the sign-in page
in the dialog. For an htmx request, a redirect to sign-in is answered
instead with `HX-Redirect` to the sign-in URL with `next` set to the
page's address (`HX-Current-URL`), by a small decorator or middleware
for the dialog's views.

**Focus and keys.** `showModal()` makes the page behind inert, moves
focus into the dialog and closes it on Escape; closing returns focus
to the link that opened it. While a dialog's form is being posted, its
buttons are disabled (`hx-disabled-elt`), so a double click books
once.

## Risks / Trade-offs

- The refresh is a second request after each save. → It costs one
  page render, and spares the user a reload.
- The dialog's behaviour is script that the Django test client cannot
  run. → The tests cover what the server answers; the opening, the
  refresh and focus are checked in a browser before the merge, on the
  test server or with a headless browser run by hand.
- A refresh of a page fetched after another user's change shows that
  change too. → That is what a reload would show.
