## MODIFIED Requirements

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the structure images in `examples/demo/static/structures/`, the compound registry in `examples/demo/compounds/` and the sequences in `examples/demo/md/sequences/`. The registry holds a file for every compound a sample names, as product or substrate, and no other file, and every compound sets `name_de`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory.

The demo declares compound fields of every type (compound-fields "Field declarations"):
- **Declarations.** `examples/demo/orgsyndb.toml` declares, in this order, `item_number` (`text`, `required`, `unique`, `pattern = 'CH-\d{4}'`, `column`, `search`), `short_name` (`text`, `search`), `chemical_class` (`choice`, `required`, `multiple`, `column`, `facet`, `vocabulary = "chemical-classes"`), `stock` (`number`, `unit = "g"`, `min = 0`) and `in_house` (`boolean`, `facet`), each with a `label` and a `label_de`.
- **Vocabulary.** `examples/demo/vocabularies/chemical-classes.toml` is the demo's only vocabulary. Every value has a `label_de`, and some value has two ancestors.
- **Values.** Every compound sets `item_number` and `chemical_class`. At least one compound sets two chemical classes, and at least one a class with two ancestors. Some compounds set `short_name` and `stock` and some do not, and at least one `stock` is not a whole number. `in_house` is `true` for at least one compound, `false` for at least one, and unset for at least one.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, the demo registry's file names are exactly the keys the samples name, each with `.toml`, and neither `org/`, `md/` nor `site/static/` exists at the application root

#### Scenario: The demo declares its fields
- **WHEN** a test reads `examples/demo/orgsyndb.toml`, `examples/demo/vocabularies/` and the demo registry
- **THEN** the declarations, the vocabulary and the compounds' values meet the rules above

