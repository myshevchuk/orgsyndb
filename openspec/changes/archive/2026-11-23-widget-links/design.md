## Context

Lab record pages start with their `h1`; only the notebook page has a
plain link `Laborjournale` under its heading. List headings are the
lists' `h1`s (`Endprodukte`, `Chargen`, `Gefäße`, `Lieferungen`,
`Aufgaben`, `Substanzen`, `Laborjournale` in German). `DeliveryNote`'s
`__str__` already reads `#<pk>` for a note without a number, which the
note page uses; the overview template writes `number|default:"–"`.
The site's metadata panel writes `notebook` as text through
`field-value.html`.

## Decisions

1. **One partial for the back link.** `orgsyndb_web/back.html` takes the
   URL and the text, and writes `p.lab-back` with an
   `aria-hidden` arrow. Each page passes its list's heading by the
   same `translate` call its list page uses for the `h1`, so the two
   cannot drift; a test compares them. The link stands first in the
   page's own `main` block, so the shell's demo note and messages stay
   before it (lab-demo).
2. **`#<id>` from the model.** The overview writes the note through its
   `__str__`, the form the note's page already shows, instead of a
   second spelling.
3. **`Alle →` as the widget note**, like `Zur Planung` on `Nächste
   Synthesen`.
4. **Notebook link in `procedure-meta.html`**: for the field key
   `notebook`, the code is the value before the last `/`. Validation
   guarantees the form, so the code is URL-safe, and that the code is a
   notebook of the registry snapshot (procedure-fields "Journal
   fields"). That is not a live page: a snapshot can name a notebook
   the lab never registered or has since removed, and the link then
   answers 404, as a substance link can. The site cannot know which
   notebooks the lab serves.
5. **Which duplicate goes.** The summary exists only to be framed by
   the home page (lab-overview "Summary for the home page"), and the
   home page's link stands under the frame in the site's own text; the
   frame's link goes, so the frame shows only data.

Rejected: the inventory section tabs on record pages (the survey's
other suggestion) — four links where one is needed, and the tabs mark
the current list, which a record page is not.

## Risks / Trade-offs

- [The summary frame's height was sized with the link] → the frame
  keeps its height; the summary gains a line of air. To be checked in
  the browser (task 3.1).
- [Site links to the lab are enumerated] → site-build "Deployment
  under a path prefix" gains the notebook pages, and its two link
  tests accept them.
