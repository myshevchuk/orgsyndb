## 1. Tests

- [x] 1.1 Substances: fields, key rule and fixed key, CAS form, check
  digit and uniqueness, molar mass above zero, name by language,
  protected deletion, history
- [x] 1.2 Vocabularies: the four, key rule and fixed key, no loop in the
  form and the admin, a term in use protected
- [x] 1.3 Registry pages: list, search, substance page with its site link
  only when the index lists the key, sections, vocabulary pages in tree
  order with counts, 404s, no sign-in needed
- [x] 1.4 Registry forms: new and edit for substances and terms, at least
  one class, decimal comma, errors, redirects, sign-in required
- [x] 1.5 Registry admin: search, read-only keys, parent check
- [x] 1.6 Snapshot: shape, order, nulls, digest stability and change,
  `/lab/registry/snapshot.json` without sign-in
- [x] 1.7 `registry_load`: round trip of the demo registry, refusals
  (registry not empty, format, broken reference, invalid value), nothing
  written on failure
- [x] 1.8 `registry_import`: the demo collection, warnings, a compound
  without group or class, unreadable file; the demo registry equals the
  import plus `new-compound-7`
- [x] 1.9 Articles and items: article number once and unique, shared by
  sizes, category on the article, item identity per article, a new item
  creating its article, delivery and consumption refused without a
  number
- [x] 1.10 Lots: substance, source and supplier fixed, lots of any
  substance, filling only from a lot of the item's substance, conversion
  through the substance's molar mass
- [x] 1.11 Inventory lists, pages and forms: item list names, links and
  search; bulk list columns, order and lots without an article; item and
  lot pages; forms with the substance `datalist`, unknown keys,
  `?substance=`; admin with articles
- [x] 1.12 Tasks: substance on record, list, search, page, forms,
  `?substance=`, unknown substance, admin search, record as bulk
- [x] 1.13 Planning: matching by substance, articles without a number,
  batches by substance, bulk unit and conversions from the substance,
  plan-synthesis link with `?substance=`
- [x] 1.14 Index: compound keys only, `has_compound`, no `compound_for`;
  substance links; navigation entry
- [x] 1.15 Overview: open lots of any substance, names from articles
- [x] 1.16 Demo data: registry loaded first, records in terms of
  substances, bought and intermediate lots, `--replace` deleting the
  registry, the scenarios of every seeding day
- [x] 1.17 Table diagram: the new boxes, colours and links, the remaining
  declared links

## 2. Implementation

- [x] 2.1 `vocabulary` package: models, migration, forms, admin
- [x] 2.2 `registry` package: `Substance`, `SubstanceClass`, migration,
  forms, views, templates, admin, snapshot, the two commands
- [x] 2.3 `inventory`: `Article`, items and lots reshaped, migration
  that empties the reshaped tables; bookings, figures, forms, views,
  templates, admin
- [x] 2.4 `tasks`: substance, migration, forms, views, templates, admin
- [x] 2.5 `planning`: matching, batches, molar masses, links
- [x] 2.6 `orgsyndb_web`: index without compounds, substance link tag,
  navigation, URLs
- [x] 2.7 Overview figures and lists
- [x] 2.8 Demo: `demo/registry.json`, data set and command
- [x] 2.9 Table diagram: grid, colours, declared links, regenerate
  `webapp/docs/database-schema.html`
- [x] 2.10 German translations

## 3. Docs and archive

- [ ] 3.1 `README.md`: the registry, its pages and the two commands;
  what the lab app no longer reads from the index
- [x] 3.2 Review, then archive
