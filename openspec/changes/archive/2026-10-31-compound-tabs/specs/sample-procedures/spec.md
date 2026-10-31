## MODIFIED Requirements

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the structure images in `examples/demo/static/structures/`, the compound registry in `examples/demo/compounds/` and the sequences in `examples/demo/md/sequences/`. The registry holds a file for every compound a sample names, as product or substrate, and no other file, and every compound sets `name_de`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory.

The demo declares compound fields of every type (compound-fields "Field declarations"):
- **Declarations.** `examples/demo/orgsyndb.toml` declares, in this order, `item_number` (`text`, `required`, `unique`, `pattern = 'CH-\d{4}'`, `column`, `search`), `short_name` (`text`, `search`), `chemical_class` (`choice`, `required`, `multiple`, `column`, `facet`, `vocabulary = "chemical-classes"`), `stock` (`number`, `unit = "g"`, `min = 0`), `in_house` (`boolean`, `facet`) and `group` (`choice`, `required`, `facet`, `tabs`, `vocabulary = "inventory-groups"`), each with a `label` and a `label_de`; `group` is labelled `Group` and `Gruppe`.
- **Vocabularies.** `examples/demo/vocabularies/` holds exactly `chemical-classes.toml` and `inventory-groups.toml`, and every value of both has a `label_de`. Some value of `chemical-classes` has two ancestors. `inventory-groups` holds, in this order, `purchased` (`Purchased`, `Zugekauft`), `starting-materials` (`Starting materials`, `Ausgangsstoffe`) and `reagents` (`Reagents`, `Reagenzien`), both under `purchased`, `synthesised` (`Synthesised`, `Selbst hergestellt`), and `intermediates` (`Intermediates`, `Zwischenprodukte`) and `final-products` (`Final products`, `Endprodukte`), both under `synthesised`.
- **Values.** Every compound sets `item_number`, `chemical_class` and `group`, a `group` of `starting-materials`, `reagents`, `intermediates` or `final-products`, each of them set by some compound; ten compounds are purchased and ten synthesised. At least one compound sets two chemical classes, and at least one a class with two ancestors. Some compounds set `short_name` and `stock` and some do not, and at least one `stock` is not a whole number. `in_house` is `true` for at least one compound, `false` for at least one, and unset for at least one.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, the demo registry's file names are exactly the keys the samples name, each with `.toml`, and neither `org/`, `md/` nor `site/static/` exists at the application root

#### Scenario: The demo declares its fields
- **WHEN** a test reads `examples/demo/orgsyndb.toml`, `examples/demo/vocabularies/` and the demo registry
- **THEN** the declarations, the vocabulary and the compounds' values meet the rules above

