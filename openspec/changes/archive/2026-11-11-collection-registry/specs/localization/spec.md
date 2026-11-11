## MODIFIED Requirements

### Requirement: German compound names
A compound's shown name SHALL be its substance's `name_de` in the registry on a German site when the substance has one, and its `name` otherwise; on an English site it is its `name`. Every place the site names a compound uses the shown name: the compound's page and its `<title>`, the compound directory and its order, the metadata panel, the key facts, the catalogue's Details view, the structure `alt` texts and the index terms.

#### Scenario: German names on a German site
- **WHEN** a test reads `public/compounds/salicylic-acid/index.html`, `public/compounds/index.html` and `public/procedures/osdb-0001/index.html` of a build of the test collection in locale `de`
- **THEN** the compound page's `h1` is `Salicylsäure`, the directory links it as `Salicylsäure`, ordered among the German names, and the procedure's `Product` link reads `Salicylsäure`

#### Scenario: A compound without a German name
- **WHEN** a test builds a copy of the test collection in locale `de` after removing the `name_de` of `acetone` from the copy of its registry
- **THEN** `public/compounds/acetone/index.html` has the `h1` equal to the substance's `name`

### Requirement: German reaction-type labels
A German site SHALL show a reaction type's `label_de`, from the registry's reaction types, wherever an English site shows its `label`, and its `label` where the term has no `label_de` (reaction-types "Reaction-type data for the site"). The reaction-type lists of `/reaction_types/` and of the catalogue's reaction-type facet are ordered by the shown label.

#### Scenario: German labels for reaction types
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html`, the reaction-type list of `public/reaction_types/index.html` and the reaction-type facet of `public/procedures/index.html`, of a German build
- **THEN** the term page's `h1` is `Aldolkondensation` and its title `Aldolkondensation | OrgSynDB`
- **AND** both lists show the German labels in alphabetical order
