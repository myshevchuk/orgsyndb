## Why

A reaction with a broad scope is written once, as a general procedure,
and its homologues are listed in a scope table: which substrates give
which products, in what yield, and where conditions differ. OrgSynDB
can only hold one run per procedure, so each homologue needs a
procedure of its own, or the scope table stays prose that no compound
page, link or search can see.

## What Changes

- A procedure with `scope` is a general procedure. `scope` is a
  non-empty array of entries, each with its own `substrates` and
  `products` (with yields), and the optional structured deviations
  `scale`, `time`, `temperature` (°C) and `note`. A general procedure
  has no top-level `products` or `substrates`; it keeps its `scale` as
  the typical scale.
- Any procedure may set `scheme_image`, a reaction-scheme image shown in
  the title block instead of the product structures. A general procedure
  without one shows the placeholder.
- In Org, the scope is a table named `scope` whose header row names the
  entry keys. The export turns it into the `scope` front matter and
  leaves it out of the body; it reports a malformed table as a problem
  of the source.
- The procedure page shows the scope as a table before the body, with
  each entry's starting materials and products linked to their compound
  pages, the products' structures, yields and the deviations that any
  entry sets. The key facts give the scale and the range of yields.
- Compound pages, precursor and used-in links, the panel, the
  catalogue's Details view and the search index treat every entry's
  products and substrates as the procedure's own; a compound page names
  the entry that makes the compound.
- The catalogue gains a facet `kind`, with the values `specific` and
  `general`, and the Procedures section a tab `General procedures`,
  leading to `/general-procedures/`: the catalogue with that facet fixed
  to `general`.
- The demo collection gains a general procedure with its German
  translation.

## Capabilities

### New Capabilities

- `general-procedures`: the `scope` field and its entries, the Org
  scope table, the scope table on the page and the general-procedures
  view.

### Modified Capabilities

- `procedure-schema`: `products` required only without `scope`;
  `scheme_image`.
- `procedure-validation`: the field forms of scope problems.
- `org-export`: the scope table in the export and its problems.
- `site-theme`: the key facts, panel, structure slot, compound pages
  and links of a general procedure; the tab.
- `site-catalogue`: the `kind` facet, its rows and address, and the
  fixed scope of `/general-procedures/`.
- `site-search`: the SMILES search results that the general procedure joins.
- `localization`: the German strings, `scope` and `scheme_image` among
  the fields variants share (notes excepted), and the counts of the
  published test collection.
- `sample-procedures`: the demo's general procedure.

## Impact

- `tools/validate.py`, `tools/export.el`, `tools/osdb-org.el`.
- Site: a scope-table partial; the procedure header, panel, key facts,
  structure, links, compound pages; catalogue rows, facet and scripts;
  a section for `/general-procedures/`; i18n; styles.
- Content: a general procedure in `examples/demo/` and the test
  collection, with its compounds.
- Tests across the validator, the export, the catalogue scripts, the
  theme, the catalogue, search and localization.
- Docs: `README.md`, `docs/SCHEMA*.md`, `docs/AUTHORING*.md`,
  `docs/AUTHORING-ORG*.org`.
