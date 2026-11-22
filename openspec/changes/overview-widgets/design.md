## Context

`/lab/` renders `overview/overview.html`: a `section.lab-overview`
with five `div.overview-part`s, the first including
`overview/_summary.html` (the stock bar, a line counting the items,
and `dl.lab-figures`), which `/lab/summary/` includes alone. The home
page frames `/lab/summary/` in `iframe.home-lab-frame`, whose height
`site/assets/css/screen.css` fixes at 15 rem, 22 rem below 70 rem and
30 rem below 30 rem. The chart's bars carry their values
(`overview/chart.py`, `Bar.value`), and the stock bar's parts their
level labels, so the new presentation needs no change to the views.

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
as the item page does: each tile its label, the figure, and its
secondary text (`Vorjahr bis …`, `<n> verspätet` as the late badge,
`<m> geplant`), the figure linking where it links today.

### Stock widget and legend

A `section.widget` titled `Bestand` holding the stock bar unchanged
(`div.stock-bar`, links with `level-<level>`, `flex-grow` by count,
titled `<label>: <n>`), then a legend, a list of the levels shown,
each with a swatch carrying `level-<level>`, its label and its
number, then the number of items. The legend is presentation of the
bar's own data; the spec names it as the levels named with their
numbers.

### Layout

Below the `h1`, the figures strip across the page; then a grid of two
columns: on the left `Bestand`, `Nächste Synthesen` with its `Zur
Planung` link in the title bar, and `Abgaben je Monat`; on the right,
narrower, `Meistgefragt <year>`, `Empfänger <year>` and `Letzte
Lieferscheine`. Below 60 rem the columns stack. The grid lives in
`lab.css` under `@media screen`, as the item page's does, so print
keeps block flow. The old `.lab-overview`, `.overview-part`,
`.overview-stock`, `.overview-next`, `.overview-months`,
`.lab-figures` and `.overview-list` rules go when nothing uses them.

### Tables for the year's lists

`Meistgefragt`: `Artikelnr.` (`Article no.`), `Substanz`
(`Substance`), `Gebinde` (`Containers`); `Empfänger`: `Empfänger`
(`Recipient`), `Gebinde`; `Letzte Lieferscheine`: `Beleg` (`Note`),
`Datum` (`Date`), `Empfänger`, `Gebinde`. The containers cell holds
the number and a bar whose width is the row's share of the list's
largest count, drawn with CSS (`widthratio`), `aria-hidden`. The
number of rows shows in each title bar.

### Chart

The chart keeps its `svg` and titles; each bar gains its value as a
`text` above it, the previous year's in the muted colour, and a
legend under the chart names the two colours (`Aktuelle 12 Monate`,
`Vorjahresmonat`), replacing the caption. A value of 0 shows no
label, so that an empty lab draws no row of zeros.

### The home page's frame

The summary grows by the legend. Its height is checked in a browser
in the home page's frame at the three widths; where it no longer
fits, `.home-lab-frame`'s heights in `screen.css` are raised.

## Risks / Trade-offs

- [The frame clips the summary at some width] → checked at 1440,
  1000 and 390 px; heights adjusted in the same change.
- [Removing old overview CSS breaks another page] → each class is
  searched for in the templates before its rule goes.
