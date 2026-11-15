## Why

The registry page is headed `Substanzen` and lists the four
vocabularies as links above the table, so they read as filters of the
substances, though they are siblings: the chemical classes and the
groups describe substances, the projects and reaction types describe
procedures, and the lab notebooks, which the snapshot carries beside
them, sit in another menu entry. `Substanzen` beside `Verbindungen`
reads as two names for one thing, and the vocabulary pages count only
substances as uses, so every project and reaction type shows 0 though
procedures name them.

The owner wants substances in a group of their own, `Chemikalien`,
which will later hold commercial sources and products in development,
and the technical tables in a group `Stammdaten` before `Hilfe`, with
the imports among them. The groups vocabulary becomes
`Bestandsgruppen`, which is what it is: the snapshot already calls it
`inventory-groups`.

## What Changes

- The menu: `Labor` keeps the overview, inventory, planning and
  tasks; a new group `Chemikalien` (`Chemicals`) holds `Substanzen`;
  `Sammlung` stays; a new group `Stammdaten` (`Master data`) holds the
  chemical classes, inventory groups, projects, reaction types, lab
  notebooks and imports; `Hilfe` follows.
- The registry page loses its links to the vocabularies, and each
  vocabulary page its link back to the substances; the menu leads to
  each.
- The groups vocabulary is named `Bestandsgruppen` (`Inventory
  groups`), and a substance's group `Bestandsgruppe` (`Inventory
  group`), in the lab's pages, forms and admin.
- A vocabulary page's `Verwendet` (`In use`) counts what names each
  term: substances for the chemical classes and inventory groups,
  procedures for the projects and reaction types.
- URLs and tables stay as they are.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-registry`: "Substances", "Vocabularies" and "Registry forms"
  name the inventory groups; "Registry pages" drops the links to the
  vocabularies, names the column `Bestandsgruppe` and counts uses by
  procedures for the projects and reaction types.

## Impact

- `site/hugo.toml` and `site/i18n/` (the menu and its texts).
- `webapp/registry/` (views, templates, form, model labels),
  `webapp/vocabulary/models.py` (labels), their translations and
  label-only migrations.
- Registry tests; README and the authoring guides' menu lists.
