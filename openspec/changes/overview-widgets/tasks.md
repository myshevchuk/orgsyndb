## 1. Tests

- [ ] 1.1 Overview page: the figures strip with its four tiles, links,
  secondary text and late badge; the widget `Bestand` with the stock
  bar unchanged and the legend naming each level shown with its
  number, and the number of items; the widget `Nächste Synthesen`
  with its table and `Zur Planung`, or `Keine Prognosen.`; the widget
  `Abgaben je Monat` with the `svg`, its bars, titles and value
  labels (none for 0) and the legend; the widgets of the year's lists
  as tables with their columns, row counts and `Keine Abgaben.`; the
  scenarios of the delta, German and English
- [ ] 1.2 Summary: the same strip and stock widget, the link to the
  overview, `base target="_top"`, no `Nächste Synthesen`, table or
  `svg`
- [ ] 1.3 Existing tests in `test_overview.py` moved to the new markup
- [ ] 1.4 Static: no rule of `lab.css` outside an `@media` block sets
  the overview grid to `display: grid`

## 2. Overview and summary

- [ ] 2.1 `_figures.html` and `_stock.html` from `_summary.html`;
  `overview.html` and `summary.html` as the chosen mockup; the grid in
  `lab.css` under `@media screen`; unused overview rules removed
- [ ] 2.2 Chart value labels and legend; table proportion bars
- [ ] 2.3 German catalogue of `overview`
- [ ] 2.4 `.home-lab-frame` heights in `site/assets/css/screen.css` if
  the summary no longer fits

## 3. Verification

- [ ] 3.1 Area tests, then both suites once; CI green on the branch
- [ ] 3.2 In a browser: `/lab/` beside the mockup at 1440 px and
  narrow; the home page's frame at 1440, 1000 and 390 px; the owner
  checks it on the test server
