## 1. Tests

- [x] 1.1 Substance page: the widget `Verbindung` (`Compound`) with
  the structure figure and every value, `–` where empty, the group's
  link, the SMILES copy button beside its code; the widgets
  `Gebinde`, `Chargen` and `Aufträge` with their columns and `Keine`
  when empty; `Hergestellt nach`, `Verwendet in` and `Synthesewege`
  as tables with their columns, shown only with rows; `Herstellungswege`
  as an open `details.widget` with an `id`; the `Bearbeiten` link for
  a signed-in user; the scenarios of the delta
- [x] 1.2 Existing tests moved to the new markup:
  `test_registry_pages.py` (sections found by heading through
  `planning_support.section()`) and `test_registry_collection.py`
  (`items_under()`, which expects a list after the heading)
- [x] 1.3 Static: no rule of `lab.css` outside an `@media` block sets
  the substance grid to `display: grid`; `lab.css` no longer has
  `main > .structure`

## 2. Substance page

- [x] 2.1 `registry/substance.html` as the chosen mockup; the page's
  grid in `lab.css` under `@media screen`; the compound widget's rules
  in `site/assets/css/screen.css`; `main > .structure` removed
- [x] 2.2 German catalogue of `registry` for the new labels

## 3. Documents

- [x] 3.1 `docs/SCHEMA.md` and `docs/SCHEMA.de.md`: the order of the
  substance page's parts

## 4. Verification

- [x] 4.1 Area tests, then both suites once; CI green on the branch
- [ ] 4.2 In a browser: the page of `1-biphenyl-4-yl-ethanol` beside
  the mockup at 1440 px, and at a narrow width, in the light and the
  dark scheme; print preview; the
  owner checks it on the test server
