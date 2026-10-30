## 1. Tests and fixtures, red first

- [x] 1.1 Fixture registry `tests/fixtures/compounds/` and
  `static/structures/ethyl-acetate.svg`; every committed procedure
  fixture moved to `products` and `substrates`; `invalid/unknown-compound`
  and `invalid/unknown-substrate` in place of `missing-precursor` and
  `missing-structure-image`
- [x] 1.2 Validator: registry files and fields, `products`, `substrates`,
  `--compounds` and its default, report format, variants, fixture suite
- [x] 1.3 Test collection: `compounds/` as the demo registry will hold
  it, the converted samples in the new shape
- [x] 1.4 Pipeline: the overlay's six mounts, `init` creating
  `compounds/`, `validate`'s arguments; the export of `:products`
- [x] 1.5 Samples: seeds, theme sample set, chains, compound weights,
  German twins, the demo registry
- [x] 1.6 Templates: the procedure templates' `products`, the compound
  template
- [x] 1.7 Site: navigation, key facts, panel, derived links, structure
  figures, compound pages and directory, home page, Details view,
  index terms, SMILES index, findability, German names and strings;
  theme fixtures `OSDB-0907-two-products.md` and
  `OSDB-0908-second-route.md`, whose compounds the fixture registry
  holds

## 2. Implementation

- [x] 2.1 `tools/validate.py`: the registry, `products`, `substrates`,
  `--compounds`; `tools/orgsyndb` and `tools/pipeline.py`: validate
  arguments, overlay mounts, `init`
- [x] 2.2 `tools/export.el`: arrays of tables written last
- [x] 2.3 Demo collection: `compounds/`, the samples and their German
  twins in the new shape, the structure image renamed
- [x] 2.4 Templates: `procedure.md`, `procedure.de.md`, `procedure.org`,
  `procedure.de.org`, and the new `compound.toml`
- [x] 2.5 Site: the compound content adapter and layouts, the procedure
  partials, catalogue details, index terms and SMILES index, home page,
  navigation, i18n strings, styles

## 3. Verification

- [x] 3.1 Full suite: 490 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: a procedure with one and with two products, a
  compound page and the directory, light and dark, at 1280 and 500 CSS
  pixels; the copy button of a compound page and a procedure page; the
  catalogue's Details view and the SMILES searches of site-search
  "Every sample is findable"; the CAS numbers of the demo registry
  against PubChem. Checked in headless Firefox on the
  German demo build and on the test collection with OSDB-0907 added:
  OSDB-0002 links its product and both starting materials and keeps
  formula, weight, CAS and SMILES; OSDB-0907 gives two yields, a
  `Produkte` pair and one figure; the salicylic acid and isopentyl
  acetate pages show their facts, image and lists at 1280 and 500 in
  both schemes; the directory lists 17 compounds with their counts.
  The catalogue Details view, the SMILES searches and the copy button
  are covered by the integration and search tests, not re-checked by
  hand. All 17 CAS numbers resolve on PubChem to the named compound
  with the same formula

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA*.md`,
  `docs/AUTHORING*.md`, `docs/AUTHORING-ORG*.org`
- [x] 4.2 Codex reviewer: one finding, compound names escaped twice;
  fixed with a regression test
- [x] 4.3 Archive
