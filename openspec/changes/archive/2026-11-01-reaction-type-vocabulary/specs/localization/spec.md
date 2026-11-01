## MODIFIED Requirements

### Requirement: German reaction-type labels
A German site SHALL show a reaction type's `label_de`, from the collection's `vocabularies/reaction-types.toml`, wherever an English site shows its `label`, and its `label` where the value has no `label_de` (reaction-types "Reaction-type data for the site"). Every value of the starter vocabulary `templates/reaction-types.toml` has a `label_de` (reaction-types "Starter reaction types"). The reaction-type lists of `/reaction_types/` and of the catalogue's reaction-type facet are ordered by the shown label. The validator refuses, as a configuration error, a reaction-type vocabulary whose `label_de` is not a non-empty string.

#### Scenario: Vocabulary with German labels
- **WHEN** a test loads `templates/reaction-types.toml`, and makes a settings variant run on `baseline` that adds `label_de = " "` to the value `esterification` of `vocabularies/reaction-types.toml`
- **THEN** every value of the starter vocabulary has a non-empty `label_de`, and the run exits 2 naming `label_de`

#### Scenario: German labels for reaction types
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html`, the reaction-type list of `public/reaction_types/index.html` and the reaction-type facet of `public/procedures/index.html`, of a German build
- **THEN** the term page's `h1` is `Aldolkondensation` and its title `Aldolkondensation | OrgSynDB`
- **AND** both lists show the German labels in alphabetical order
