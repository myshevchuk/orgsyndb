## Context

`/lab/` renders `overview/overview.html`: a `section.lab-overview`
with five `div.overview-part`s, the first including
`overview/_summary.html` (the stock bar, a line counting the items,
and `dl.lab-figures`), which `/lab/summary/` includes alone. The home
page frames `/lab/summary/` in `iframe.home-lab-frame`, whose height
`site/assets/css/screen.css` fixes at 15 rem, 22 rem below 70 rem and
30 rem below 30 rem. The chart's bars carry their values
(`overview/chart.py`, `Bar.value`), and the stock bar's parts their
level labels. The chart's drawing leaves 10 units above the tallest
bar (`TOP`), too little for a value label, and gives a bar no centre
to place one at; `chart.py` is the one Python file the change
touches. The route `/lab/` must keep answering with a
`section.lab-overview` (web-app "Paths under /lab/").

The owner chose mockup B of the UI survey, kept outside the
repository; this design states what the change takes from it.

## Goals / Non-Goals

**Goals:**

- The overview as mockup B, from the widget classes in place, with the
  data it shows today and a legend for the stock bar.
- The summary showing the same figures strip and stock widget, still
  fitting its frame on the home page.

**Non-Goals:**

- New links: the mockup's `Alle Artikel →` beside the stock and `Alle
  →` beside the latest notes, and `#<id>` for a note without a number,
  come with the later links change. The duplicate overview link
  inside and outside the home page's frame stays for that change too.
- The mockup's count of late tasks in the `Nächste Synthesen` title
  bar, which repeats a figure; the figure keeps it.
- Sorting: the tables have at most five rows.

## Decisions

### Shared parts of overview and summary

`_summary.html` splits into `_figures.html`, the figures strip, and
`_stock.html`, the stock widget; the overview and the summary include
both, the strip first. The strip uses `.figures-strip`/`.figure-tile`
as the item page does: each tile its label, the figure and its
secondary text, the figure linking where it links today. `Abgegeben
<year>` shows the containers with `Vorjahr bis <date>: <n>` under
them; `Fällige Synthesen` the number with the late badge; `Aufgaben`
the existing string `<n> laufend · <m> geplant` as its value, one
link to `/lab/tasks/`; `Offene Gefäße` the number.

### Stock widget and legend

A `section.widget` titled `Bestand` holding the stock bar unchanged
(`div.stock-bar`, links with `level-<level>`, `flex-grow` by count,
titled `<label>: <n>`), then a legend, a list of the levels shown,
each with a swatch carrying `level-<level>`, its label and its
number, then the number of items. The legend is presentation of the
bar's own data; the spec names it as the levels named with their
numbers.

### Layout

Below the `h1`, one `section.lab-overview` holds the page's widgets:
the figures strip across the page; then a grid of two
columns: on the left `Bestand`, `Nächste Synthesen` with its `Zur
Planung` link in the title bar, and `Abgaben je Monat`; on the right,
narrower, `Meistgefragt <year>`, `Empfänger <year>` and `Letzte
Lieferscheine`. Below 60 rem the columns stack. The grid lives in
`lab.css` under `@media screen`, as the item page's does, so print
keeps block flow. The old `.lab-overview`, `.overview-part`,
`.overview-stock`, `.overview-next`, `.overview-months`,
`.lab-figures`, `.overview-list` and `.deliveries-chart figcaption`
rules go when nothing uses them.

### Tables for the year's lists

`Meistgefragt`: `Artikelnr.` (`Article no.`), `Substanz`
(`Substance`), `Gebinde` (`Containers`); `Empfänger`: `Empfänger`
(`Recipient`), `Gebinde`; `Letzte Lieferscheine`: `Beleg` (`Note`,
with the message context `delivery note`, since the `tasks` catalogue
translates a bare `Note` as `Notiz` and wins the merge), `Datum`
(`Date`), `Empfänger`, `Gebinde`; an empty recipient reads `–`. In
the two ranking lists the containers cell holds the number and a bar
whose width is the row's share of the first row's count, the list's
largest (`widthratio`), `aria-hidden`; the latest notes, ordered by
date, have no bar. The number of rows shows in each title bar; an
empty list has no count and reads `Keine Abgaben.`

### Chart

The chart keeps its `svg` and titles; each bar gains its value as a
`text.chart-value` above it, the previous year's in the muted colour,
and a legend under the chart names the two colours (`Aktuelle 12
Monate`, `Vorjahresmonat`), replacing the caption. A value of 0 shows
no label, so that an empty lab draws no row of zeros. `chart.py`
raises `TOP` so that a label above the tallest bar stays inside the
drawing, and gives each `Bar` its centre, `label_x`, and the label's
baseline, `label_y`, so that the template places labels without
arithmetic.

### The home page's frame

The summary grows by the legend. Its height is checked in a browser
in the home page's frame at 1440, 1000, 500 and 390 px, with the
demo note a demo database shows above it; where it no longer fits,
`.home-lab-frame`'s heights in `screen.css` are raised.

## Risks / Trade-offs

- [The frame clips the summary at some width] → checked at 1440,
  1000, 500 and 390 px with the demo note; heights adjusted in the
  same change.
- [Removing old overview CSS breaks another page] → each class is
  searched for in the templates before its rule goes.
