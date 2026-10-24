## Layout

Use the desktop layout as the screen default. A 96rem shell provides room
for data tables without stretching indefinitely on very wide monitors.
The home page has a flexible recent-procedures column and a 19rem browse
column. Smaller browser windows reduce or stack these columns.

The owner chose two minimalist layouts:

- **Lists: full-width table.** `/procedures/` and `/procedures-by-date/`
  show the title with the entry count, one tool row (search on the left,
  reaction-type and status selects on the right), the sort links
  right-aligned, and a table across the shell whose status column reads
  as plain text. The search field submits to `/search/`, so it works
  without JavaScript. The selects filter the rows in place:
  `list-filter.js` reveals them and hides rows by their
  `data-reaction-types` and `data-status`. Without JavaScript they stay
  hidden and the table is complete. The sort links stay links, because
  each order is its own static page.
- **Procedures: Marginalia.** The body is a reading column of up to
  48rem on the left. The structure and metadata form an unboxed margin
  of 15-21rem on the right, the structure first. CSS grid areas place
  them; the details stay first in the document, so print, Pagefind and
  windows under 55rem keep the order details, then body.

On screen the interface uses the system sans-serif stack. Paper keeps
the text face of tokens.css, so the A4 output does not change.

The navigation marks the current page with `aria-current="page"` and
the current section with `aria-current="true"`, which the screen
stylesheet underlines.

Not implemented:
- Marginalia sidenotes beside their sections, because moving body
  notes out of the Notes section would change the document order;
- a pager on the lists, because the lists have no pages.

## Rendering and accessibility

Keep layout rules in screen.css so browsers and WeasyPrint retain the
existing single-column A4 flow. Add neutral wrappers around the procedure
details and body without changing document or Pagefind indexing order.
Keep keyboard-focusable table scrolling, headings, labels and navigation.
Both color schemes continue to use the existing contrast-tested tokens.

## Stale pages after a rebuild

`orgsyndb serve` used the standard library handler, which sends
`Last-Modified` but no `Cache-Control`. Browsers then cache pages by
heuristic freshness, so after a rebuild they kept showing the earlier
HTML, which names the earlier fingerprinted stylesheets: the new layout
did not appear. `serve` now sends `Cache-Control: no-cache` on every
response, and the Caddyfile example sets the same header, so browsers
revalidate (a 304 when nothing changed) and show each new build at once.

## Verification

Build the German demo and run the full suite, including English/German
index queries and A4 PDF content checks. Inspect static desktop renders.
Live browser visual checks remain unavailable because this session has no
browser-control tool; static renders are not browser screenshots.
