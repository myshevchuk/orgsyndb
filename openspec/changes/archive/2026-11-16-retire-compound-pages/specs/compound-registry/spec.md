## MODIFIED Requirements

### Requirement: Registry checks
The validator SHALL take the registry from the snapshot file its `--registry` option names (procedure-validation "Command-line interface"): the compound keys are the keys of its substances, and its vocabularies are those procedure fields and reaction types name (procedure-fields "Procedure field declarations", reaction-types "Reaction-type vocabulary"). It checks no substance's values: the lab application checks them.

#### Scenario: Unknown compound
- **WHEN** a registry variant run removes the substance `ethyl-acetate` from the fixture snapshot
- **THEN** it reports one error for each procedure of the run that names `ethyl-acetate`, containing `unknown compound "ethyl-acetate"`

#### Scenario: A substance with the key group
- **WHEN** a registry variant run adds a substance with the key `group` to the fixture snapshot
- **THEN** it reports no problem
