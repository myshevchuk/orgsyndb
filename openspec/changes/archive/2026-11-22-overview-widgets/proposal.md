## Why

The lab overview stacks five headed bands: an unlabelled stock bar,
a definition list of figures, a table, a chart whose values show only
on hover, and three numbered lists whose values run together without
column headers. The owner chose mockup B of the UI survey
(2026-11-22) for it, the third page to move onto the widgets of
web-app "Widgets".

## What Changes

- The four figures become a figures strip at the top, the same
  widget the item page uses; the summary framed on the home page
  shows the same strip.
- The stock bar moves into a widget `Bestand` with a legend naming
  each level with its number, on the overview and in the summary.
- `Nächste Synthesen` and `Abgaben je Monat` become widgets in the
  wide left column; the chart shows each bar's value and a legend for
  the current and the previous year.
- `Meistgefragt`, `Empfänger` and `Letzte Lieferscheine` become table
  widgets in a right column, with column headers; the two ranking
  lists show a proportion bar beside each count.
- **BREAKING** (spec text only) The Overview page requirement stops
  prescribing its `h2` headings, the `dl.lab-figures` and the `ol`
  lists; it names the data and its order instead. The page keeps its
  `section.lab-overview`, which web-app "Paths under /lab/" names. The Summary requirement's scenario follows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-overview`: Overview page and Summary for the home page — data
  in widgets instead of fixed markup; the stock gains a legend of its
  levels with their numbers.

## Impact

- Templates: `overview/overview.html`, `overview/_summary.html`,
  `overview/summary.html`.
- `overview/chart.py`: room above the bars and label coordinates.
- `lab.css` (the overview's grid under `@media screen`; the old
  `.overview-*`, `.lab-figures` and chart-caption rules that no page
  uses afterwards removed); `site/assets/css/screen.css` for rules
  other pages can reuse and for `.home-lab-frame`'s heights if the
  summary no longer fits.
- German catalogue of `overview` for new labels.
- Tests: `test_overview.py` reads the old markup.
- The home page frames the summary: its height may change.
