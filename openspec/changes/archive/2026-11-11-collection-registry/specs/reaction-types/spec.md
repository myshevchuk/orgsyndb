## MODIFIED Requirements

### Requirement: Reaction-type vocabulary
A collection's reaction types SHALL be the terms of the vocabulary `reaction-types` of its registry (compound-registry "Reading the registry"), a single level of terms kept in the lab application (lab-registry "Vocabularies"). A registry without reaction types gives the collection none, so the reaction type of each of its procedures is unknown (procedure-schema "Controlled reaction type"). A declared `choice` field may name the vocabulary `reaction-types` like any other (procedure-fields "Procedure field declarations").

#### Scenario: The registry's reaction types
- **WHEN** a registry variant run makes `reductive-amination` (`label` `Reductive amination`) the only reaction type of the copy, once on a content root holding the baseline with `reaction_types = ["reductive-amination"]` and once on the baseline unchanged
- **THEN** the first exits 0 and prints nothing to stdout
- **AND** the second reports exactly one error, field `reaction_types`, containing `unknown reaction type "esterification"`

#### Scenario: A declared field names the reaction types
- **WHEN** a procedure-field run (procedure-fields "Procedure field fixture") appends to `orgsyndb.toml` the declaration of `fields.procedure` `side_reaction` (`choice`, labelled `Side reaction`, `vocabulary = "reaction-types"`) and sets `side_reaction = "reduction"` in `OSDB-0100-baseline.md`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Reaction-type data for the site
`pipeline.reaction_types_data(registry, language)` SHALL return the reaction-type data that the build stages as `build/data/reaction_types.json` (build-script "build subcommand"), given the collection's registry and the site's language. The data is a table with one key per reaction type of the registry, each mapped to a table holding only `label`: the term's `label_de` when the language is `de` and the term has one, its `label` otherwise. A registry without reaction types gives an empty table.

The site reads the data as `site.Data.collection.reaction_types` (site-build "Hugo configuration"). Wherever it shows a reaction type's vocabulary label (site-theme, site-catalogue, synthesis-sequences), the label is the data's `label` for that reaction type.

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

## REMOVED Requirements

### Requirement: Starter reaction types
**Reason**: Reaction types are terms of the lab application's registry; a collection holds no vocabulary file to start from.
**Migration**: Create reaction types in the registry's vocabulary pages, or import a collection's `vocabularies/reaction-types.toml` with `manage.py registry_import`.
