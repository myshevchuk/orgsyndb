## MODIFIED Requirements

### Requirement: Field data for the site
`pipeline.fields_data(settings, registry, language)` SHALL return the field data that the build stages as `build/data/fields.json` (build-script "build subcommand"), given the path of the collection's settings file, the collection's registry (compound-registry "Reading the registry") and the site's language. The data is a table whose keys are `compound` and `procedure`, and no other. `procedure` is as procedure-fields "Procedure field data" states. `compound` holds one table per registry field (Registry fields), in their order, each with these keys and no other:
- `key`, `type` and `column`, as Registry fields states them;
- `facet`: only for a `choice` field;
- `search` and `beside`: only for a `text` field;
- `label`: the field's shown label, the German one on a German site and the English one otherwise;
- `multiple` and `tabs`: only for a `choice` field;
- `values`: only for a `choice` field, a table holding every term of its vocabulary in the registry under the term's key, each a table of `label`, the term's shown label, its `label_de` on a German site when it has one and its `label` otherwise; `path`, the shown labels of the term's ancestors, outermost first, followed by its own; and `ancestors`, the keys of its ancestors, outermost first;
- `order`: only for a `choice` field, the keys of every term of its vocabulary, each top-level term followed by the terms filed under it, recursively, siblings in key order.

A settings file that does not exist, or that declares no procedure field, gives `procedure` the journal fields alone (procedure-fields "Journal fields"); `compound` always lists the four registry fields.

#### Scenario: Field data in both languages
- **WHEN** a test calls `fields_data` on the test collection's `orgsyndb.toml` and registry with the language `en`, and again with `de`
- **THEN** each lists under `compound` the four registry fields in order with the stated keys; `chemical_class` has `multiple` `true`, `column` `true` and `facet` `true`; `group` has `tabs` `true` and `multiple` `false`
- **AND** in `en` the term `ketones` of `chemical_class` has the label `Ketones` and the path `["Carbonyl compounds", "Ketones"]`, and in `de` the label `Ketone` and the path `["Carbonylverbindungen", "Ketone"]`; `article_number` has the label `Article no.` in `en` and `Artikelnr.` in `de`
- **AND** `article_number` and `short_name` have `search` `true` and `beside` `true`, the term `ketones` has the `ancestors` `["carbonyl-compounds"]`, and the `order` of `chemical_class` begins with `alcohols`, `aryl-halides`, `carbonyl-compounds`, `acid-derivatives`, `anhydrides` and `esters`

#### Scenario: Depth-first order
- **WHEN** a test calls `fields_data` with a registry whose chemical classes are `esters` and `ketones` under `carbonyl-compounds`, `alcohols`, and `aryl-ketones` under `ketones`
- **THEN** the `order` of `chemical_class` is `["alcohols", "carbonyl-compounds", "esters", "ketones", "aryl-ketones"]`, and `aryl-ketones` has the `ancestors` `["carbonyl-compounds", "ketones"]`

#### Scenario: No settings file
- **WHEN** a test calls `fields_data` on a path that does not exist, with the test collection's registry
- **THEN** its `procedure` lists the two journal fields alone and its `compound` lists the four registry fields
