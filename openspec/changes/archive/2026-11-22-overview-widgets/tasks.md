## 1. Tests

- [x] 1.1 Overview page: the figures strip with its four tiles, links,
  secondary text and late badge; the widget `Bestand` with the stock
  bar unchanged and the legend naming each level shown with its
  number, and the number of items; the widget `Nächste Synthesen`
  with its table and `Zur Planung`, or `Keine Prognosen.`; the widget
  `Abgaben je Monat` with the `svg`, its bars, titles, the twelve
  month labels, `text.chart-value` labels (none for 0, each inside
  the drawing) and the legend; `chart.py`'s bars with `label_x` and
  `label_y`; the most requested linking their first items; the widgets of the year's lists
  as tables with their columns, row counts and `Keine Abgaben.`; the
  scenarios of the delta, German and English
- [x] 1.2 Summary: the same strip and stock widget, the link to the
  overview, `base target="_top"`, no `Nächste Synthesen`, table or
  `svg`
- [x] 1.3 Existing tests in `test_overview.py` moved to the new markup
- [x] 1.4 Static: the overview grid, `.overview-grid`, is set to
  `display: grid` under `@media screen` in `lab.css` and by no rule
  outside an `@media` block; `/lab/` keeps its `section.lab-overview`

## 2. Overview and summary

- [x] 2.1 `_figures.html` and `_stock.html` from `_summary.html`;
  `overview.html` and `summary.html` as the chosen mockup; the grid in
  `lab.css` under `@media screen`; unused overview rules removed
- [x] 2.2 `overview/chart.py`: headroom and label coordinates; chart
  value labels and legend; proportion bars in the two ranking lists
- [x] 2.3 German catalogue of `overview`
- [x] 2.4 `.home-lab-frame` heights in `site/assets/css/screen.css` if
  the summary no longer fits

## 3. Verification

- [x] 3.1 Area tests, then both suites once; CI green on the branch
- [x] 3.2 In a browser: `/lab/` beside the mockup at 1440 px and
  narrow; the home page's frame at 1440, 1000, 500 and 390 px with the
  demo note; the owner
  checks it on the test server
