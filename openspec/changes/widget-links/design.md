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
   cannot drift; a test compares them.
2. **`#<id>` from the model.** The overview writes the note through its
   `__str__`, the form the note's page already shows, instead of a
   second spelling.
3. **`Alle →` as the widget note**, like `Zur Planung` on `Nächste
   Synthesen`.
4. **Notebook link in `procedure-meta.html`**: for the field key
   `notebook`, the code is the value before the last `/`. Validation
   guarantees the form and that the notebook exists in the registry
   (procedure-fields "Journal fields"); the link may still lead to a
   page the lab removed later, as the substance links may.
5. **Which duplicate goes.** The summary exists only to be framed by
   the home page (lab-overview "Summary for the home page"), and the
   home page's link stands under the frame in the site's own text; the
   frame's link goes, so the frame shows only data.

Rejected: the inventory section tabs on record pages (the survey's
other suggestion) — four links where one is needed, and the tabs mark
the current list, which a record page is not.

## Risks / Trade-offs

- [The summary frame's height was sized with the link] → the frame
  keeps its height; the summary gains a line of air. Checked in the
  browser.
