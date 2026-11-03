## 1. Tests and fixtures, red first

- [x] 1.1 Pipeline: `routes_data` on the test collection, a protection
  and its removal, the depth limit, the step budget, order, entries and
  a step from nothing (synthesis-routes "Derived routes")
- [x] 1.2 Build: `build/data/routes.json` is staged (build-script "build
  subcommand")
- [x] 1.3 Fixtures: `tests/fixtures/theme/OSDB-0910-aspirin-hydrolysis.md`,
  a valid specific procedure making `salicylic-acid` from
  `acetylsalicylic-acid`, and `tests/fixtures/compounds/acetylsalicylic-acid.toml`
  in the fixture registry, which holds a file for every key a committed
  fixture outside `invalid/` and `collection/` names. The chain
  procedure OSDB-0911 and its compounds are written by the test into
  the sandbox, not committed
- [x] 1.4 Site: the route trees of the English theme build against the
  data, the aspirin tree, two steps to one compound, the cycle and the
  depth limit on a copy build with OSDB-0910 and OSDB-0911, the German
  tree, the stylesheet rules (synthesis-routes "Routes on compound
  pages"); the order of the compound page's sections (site-theme
  "Compound pages"); the notes after the route tree's compound links
  (compound-fields "Values beside compound links"); the German strings
  (localization "Interface strings")

## 2. Implementation

- [x] 2.1 `tools/pipeline.py`: `routes_data`
- [x] 2.2 `tools/orgsyndb`: the build writes `build/data/routes.json`
- [x] 2.3 Site: the compound page's last section and a recursive partial
  for the tree; the interface strings in `site/i18n/en.toml` and
  `de.toml`; the `.route-tree` rules in `base.css`

## 3. Documents

- [x] 3.1 The README's feature list, and any document that describes
  compound pages or the build's staged data (doc writer)

## 4. Verification

- [x] 4.1 Full suite: 1072 passed and 1 skipped (`caddy`)
- [x] 4.2 Browser: the route trees of a demo build at 1280 and 500 CSS
  pixels, light and dark, readable and without horizontal scrolling.
  Driven through Marionette in headless Firefox on a German build of a
  copy of the demo with a seven-step chain of long names added: the
  trees of `acetylsalicylic-acid`, `1-biphenyl-4-yl-ethanol` and the
  chain read as nested lists with a rule line in the computed colour of
  `--border` (`#c8c8c8` light, `#3d4147` dark); no tree overflowed at
  500 pixels, the innermost item of the six-step chain keeping about
  270 pixels; the cut-off compound ended with `weitere Stufen auf ihrer
  Seite`. The page's `h1` overflowed by 52 pixels at 500 pixels for the
  chain's long name, as compound pages already did before this change
