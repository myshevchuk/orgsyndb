## Why

A procedure carries its product inside itself: one `product` table, one
`yield_percent` and one `structure_image`, and it names the procedures
it builds on by ID in `precursors`. That model assumes a compound
belongs to one procedure. It does not: one compound may be made by
several procedures, a procedure may give two usable products, and a
procedure that uses a compound should not have to pick one of the
routes to it. The same data is also repeated today: every language
variant of a procedure copies the product's formula, weight, SMILES and
CAS, and a compound made by two procedures would be described twice.

## What Changes

- **BREAKING** A collection gains a compound registry: `compounds/`,
  one `<key>.toml` file per compound with its name, German name,
  formula, molecular weight, SMILES, CAS number and structure image.
  The key is the compound's identity.
- **BREAKING** A procedure names its products and starting materials
  by key: `products`, a non-empty list of `{ compound, yield_percent }`
  tables, and the optional `substrates`, a list of keys. `product`,
  `yield_percent`, `precursors` and `structure_image` leave the
  procedure schema. A procedure may have several products, each with
  its own yield.
- Precursor and used-in links are derived: a procedure's precursors
  are the procedures that make one of its substrates, and it is used in
  the procedures that take one of its products as a substrate.
- The validator checks the registry and resolves every key against it,
  with a new `--compounds` option; `tools/orgsyndb validate` passes the
  collection's `compounds/`, and `init` creates it.
- Every compound gets a page at `/compounds/<key>/` with its structure,
  formula, weight, CAS number, SMILES, and the procedures that make it
  and use it. `/compounds/` lists them all. Compounds join the site
  navigation: Procedures, Compounds, Help.
- A procedure page links its products and starting materials to their
  compound pages, shows one structure figure per product with an image,
  and gives a yield per product. The catalogue's Details view and the
  search index follow the products.
- The demo collection, the test collection, the templates and every
  fixture move to the new shape; a compound template joins the
  procedure templates.

## Capabilities

### New Capabilities

- `compound-registry`: the registry's files, fields and checks, and
  the compound template.

### Modified Capabilities

- `procedure-schema`: the required fields, `products` and `substrates`
  in place of `product`, `yield_percent`, `precursors` and
  `structure_image`, and the templates.
- `procedure-validation`: the `--compounds` option and its default,
  registry problems in the report, the fixture runs and fixtures.
- `collection`: `compounds/` in the layout and in `init`.
- `build-script`: the validator arguments of `validate`.
- `site-build`: the registry as Hugo data and the compound pages.
- `site-theme`: the navigation, the procedure header, the metadata
  panel, the derived precursor links, the structure figures, the home
  page's browse list, and the compound pages and directory.
- `site-catalogue`: the Details view.
- `site-search`: the indexed product terms and the SMILES index.
- `localization`: the German strings, German compound names and the
  fields that variants share.
- `sample-procedures`: the seeds, the theme sample set and the demo and
  test collections in the new shape, with their registry.
- `org-export`: the custom front matter that carries `products`.

## Impact

- `tools/validate.py`, `tools/pipeline.py`, `tools/orgsyndb`.
- Site: a content adapter and layouts for `/compounds/`; the procedure
  partials, catalogue row details, index terms and SMILES index; both
  i18n files; `screen.css`.
- Content: `examples/demo/` and `tests/fixtures/collection/` gain
  `compounds/`; every procedure front matter there, in `templates/` and
  under `tests/fixtures/` changes; `templates/compound.toml` is new.
- Tests across the validator, the pipeline, the samples, the theme, the
  catalogue, the search and localization.
- Docs: `README.md`, `docs/SCHEMA*.md`, `docs/AUTHORING*.md` and
  `docs/AUTHORING-ORG*.org`.
