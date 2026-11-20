## MODIFIED Requirements

### Requirement: Reaction-type data for the site
`pipeline.reaction_types_data(registry, language)` SHALL return the reaction-type data that the build stages as `build/data/reaction_types.json` (build-script "build subcommand"), given the collection's registry and the site's language. The data is a table with one key per reaction type of the registry, each mapped to a table holding only `label`: the term's `label_de` when the language is `de` and the term has one, its `label` otherwise. A registry without reaction types gives an empty table.

The site reads the data as `hugo.Data.collection.reaction_types` (site-build "Hugo configuration"). Wherever it shows a reaction type's vocabulary label (site-theme, site-catalogue, synthesis-sequences), the label is the data's `label` for that reaction type.

#### Scenario: Labels in either language
- **WHEN** a test calls `reaction_types_data` on the test collection's registry with the language `en`, and again with `de`
- **THEN** both results have exactly the keys of the registry's reaction types, each mapped to a table whose only key is `label`
- **AND** `aldol-condensation` has the label `Aldol condensation` in `en` and `Aldolkondensation` in `de`

#### Scenario: A term without a German label
- **WHEN** a test calls `reaction_types_data` with the language `de` on a copy of the test collection's registry from which the `label_de` of `esterification` is removed
- **THEN** `esterification` has the label `Esterification`

#### Scenario: No reaction types
- **WHEN** a test calls `reaction_types_data` on a registry without reaction types
- **THEN** it returns an empty table

#### Scenario: The site takes its labels from the registry
- **WHEN** a test builds a copy of the test collection in locale `en` after changing the `label` of `esterification` in the copy of its registry to `Ester formation`
- **THEN** the build exits 0, the `h1` of `public/reaction_types/esterification/index.html` is `Ester formation`, and the `/reaction_types/` list links that page with the text `Ester formation`
- **AND** the metadata panel and the procedure table row of every published procedure whose reaction type is `esterification` show `Ester formation`
