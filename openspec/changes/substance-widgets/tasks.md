## 1. Tests

- [ ] 1.1 Substance page: the heading line with key, group and
  classes; the compound widget with the structure figure and every
  row in order, `–` where empty, the SMILES copy button; the widgets
  `Gebinde`, `Chargen` and `Aufträge` with their columns and `Keine`
  when empty; `Hergestellt nach`, `Verwendet in` and `Synthesewege`
  as tables with their columns, shown only with rows; `Herstellungswege`
  as an open `details.widget` with an `id`; the `Bearbeiten` link for
  a signed-in user; the scenarios of the delta
- [ ] 1.2 Existing tests moved to the new markup:
  `test_registry_pages.py` and `test_registry_collection.py` (the
  `dl.metadata`, the `ul.lab-links` lists and their middot lines)

## 2. Substance page

- [ ] 2.1 `registry/substance.html` as the chosen mockup; the page's
  grid in `lab.css` under `@media screen`
- [ ] 2.2 German catalogue of `registry` for the new labels

## 3. Verification

- [ ] 3.1 Area tests, then both suites once; CI green on the branch
- [ ] 3.2 In a browser: the page of `1-biphenyl-4-yl-ethanol` beside
  the mockup at 1440 px, and at a narrow width; print preview; the
  owner checks it on the test server
