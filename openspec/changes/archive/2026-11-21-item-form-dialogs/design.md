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
the partial and the page's `h1` outside it. A request is for a dialog
when it carries `HX-Request` and not `HX-History-Restore-Request`
(htmx 2.0.11 sends both on a history-cache miss). For a dialog the
item's views render `inventory/form.html#form` with a context flag
`dialog`, and the whole page otherwise; they send
`Vary: HX-Request, HX-History-Restore-Request`. Only with `dialog` does
the form carry `hx-post` to its own URL (an explicit `action`), its
target the dialog's body and `hx-disabled-elt`; the form page posts as
a plain form, so a form opened in a new tab works as before. Errors,
a refused booking, including the form-level refusal of a movement
already reversed, and `Menge vorschlagen` then answer the partial
again with no further code. `item_fill` renders the template itself
on the `Menge vorschlagen` branch, so it takes the same choice. The
dialog handling is opted into by the five item views; `form_page` and
`saved` keep their behaviour for every other form, the delivery note
with its own template among them. Its `Abbrechen` stays a link to the
cancel URL; `lab.js` closes the dialog on a plain click on it.

**The answer to a save.** `saved` stores the message as now. For an
htmx request it answers `204 No Content` with
`HX-Trigger: {"lab-saved": {"item": <id>}}` instead of the redirect;
htmx swaps nothing on a 204 and still fires the event. Any other
request is redirected as before. Only a request for a dialog gets the
204.

**Refreshing in place.** On `lab-saved`, `lab.js` fetches the page's
own address as a page (no `HX-Request`), parses the answer, and
replaces by `id` each element of the page marked `data-refresh` with
its counterpart, and the messages, and sets `document.title` from it;
it calls `htmx.process` on what it put in. Only then does it close
the dialog, so no row can be chosen while the refresh runs; the
dialog's buttons stay disabled until then. The message is consumed by
that fetch, so it shows exactly once. What the pages mark:
- the item page: one wrapper around all of `main`'s content below the
  demo mark and messages, heading and actions included, since the
  first article number changes the heading and the links, and
  `stocked_on` the mark `neu`;
- the item list: the heading's count, the summary below the filters,
  the stock filter's menu, the choices of the other filters, the
  table's body and the details pane. The whole body is replaced
  because a save can reorder rows, move rows into or out of the
  filters and recolour other rows' heat, and a filling changes the
  bulk shown for sibling sizes.

After replacing the list's body, `lab.js` ticks again the check boxes
of the items ticked before that are still listed, re-applies the rows'
`tabindex` while the details show, and synchronizes the selection with
the new pane: the row whose `data-item` is the pane's is marked
`aria-current`, and the address's `detail` names it, or is removed
when the list is empty. When the item chosen before is still listed,
the server chose it again through `detail`, so the choice stays; when
it left the filters, the first item listed is chosen, as a reload
would. Focus goes back to the link that opened the dialog when it is
still in the page, and to the pane or page heading otherwise.

Considered: an out-of-band swap rendered by the save itself. Rejected:
the save would need to know which page it was opened from and render
that page's parts; the fetch keeps every view rendering only itself.
Considered: replacing `main`. Rejected: it would reset the view
controls and the list's ticked check boxes.

**Signed out meanwhile.** `login_required` redirects to the sign-in
page and the browser follows the 302 before htmx sees it, so htmx
would show the sign-in page in the dialog. The five item views use a
decorator that, for a request for a dialog without a signed-in user,
answers `204` with `HX-Redirect` to the sign-in URL and `next` the
page's whole address from `HX-Current-URL`, encoded as one value so
its query survives, only when it is a path on this host; otherwise
`next` is the form's path, as `login_required` sets it. htmx assigns
`HX-Redirect` to the location. Django's `LoginView` checks `next` again
before following it after sign-in.

**Focus and keys.** `showModal()` makes the page behind inert, moves
focus into the dialog and closes it on Escape; closing returns focus
as Refreshing in place says. While a dialog's form is being posted, its
buttons are disabled (`hx-disabled-elt`), so a double click books
once.

## Risks / Trade-offs

- The refresh is a second request after each save. → It costs one
  page render, and spares the user a reload.
- The dialog's behaviour is script that the Django test client cannot
  run, and the owner decided against browser tests in the suite. →
  The tests cover what the server answers: the partial or the page,
  errors, bookings, headers, the message on the next page, and the
  marked parts of freshly rendered pages. Opening, the refresh, the
  selection and focus are checked in a browser by hand before the
  merge, against the cases task 3.2 lists.
- A refresh of a page fetched after another user's change shows that
  change too. → That is what a reload would show.
