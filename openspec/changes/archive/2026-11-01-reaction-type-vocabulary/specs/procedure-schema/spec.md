## MODIFIED Requirements

### Requirement: Controlled reaction type
The `reaction_types` field SHALL be a list of exactly one string, and that string SHALL be a reaction type of the collection, a value of its `vocabularies/reaction-types.toml` (reaction-types "Reaction-type vocabulary"). A string that is not gets an error whose message contains `unknown reaction type "<v>"` and `vocabularies/reaction-types.toml`.

#### Scenario: Reaction type outside the vocabulary
- **WHEN** a fixture run on `invalid/unknown-reaction-type` examines `OSDB-0111-unknown-reaction-type.md`, whose `reaction_types` is `["esterfication"]`
- **THEN** it reports exactly one error, field `reaction_types`, containing `unknown reaction type "esterfication"` and `vocabularies/reaction-types.toml`

#### Scenario: Two reaction types
- **WHEN** a variant run sets `reaction_types = ["esterification", "reduction"]`, both in the fixture vocabulary, under the file name `OSDB-0100-two-reaction-types.md`
- **THEN** it reports exactly one error, field `reaction_types`, containing `must contain exactly one reaction type`

### Requirement: Markdown template
The file `templates/procedure.md` SHALL be a complete procedure using the placeholder ID `OSDB-0000` and slug `osdb-0000`. It satisfies the following:
- Its front matter explains every field in TOML comments and shows the optional fields commented out. The comment on `reaction_types` names `vocabularies/reaction-types.toml` as the list of allowed values, and no line of the template names `site/data`.
- Its body has the eight sections, a Reagents table with the header `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, and numbered lists under Procedure and Notes.
- Its `products` names the compound key `example-compound`, and its commented-out `substrates` line names the same key.
- Once `OSDB-0000` is replaced by a real ID and `osdb-0000` by its lowercase form, it validates with no errors and no warnings in a collection whose reaction types are `templates/reaction-types.toml` (reaction-types "Starter reaction types") and whose registry holds `templates/compound.toml` as `example-compound.toml`.

#### Scenario: Substituted Markdown template is clean
- **WHEN** a test copies `templates/procedure.md` to a temporary directory as `OSDB-0001-template.md`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, copies `templates/compound.toml` into a temporary registry as `example-compound.toml`, writes a settings file `orgsyndb.toml` holding `format = 1` beside a `vocabularies/reaction-types.toml` copied from `templates/reaction-types.toml`, and runs the validator on that directory with that registry and `--settings` naming that settings file
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Unsubstituted Markdown template is rejected
- **WHEN** a test copies `templates/procedure.md` unchanged to a temporary directory as `OSDB-0000-template.md` and runs the validator on it
- **THEN** the exit status is 1, and stdout contains an error with field `id` containing `must be between OSDB-0001 and OSDB-9999`

#### Scenario: The templates name the collection's reaction types
- **WHEN** a test reads `templates/procedure.md` and `templates/procedure.de.md`
- **THEN** each contains `vocabularies/reaction-types.toml` in a comment line before its `reaction_types` line, and neither contains `site/data`

## REMOVED Requirements

### Requirement: Reaction-type vocabulary file
**Reason**: The reaction types are the collection's own vocabulary, no longer a file of the application.
**Migration**: A collection lists its reaction types in `vocabularies/reaction-types.toml` (reaction-types "Reaction-type vocabulary"); the former list ships as `templates/reaction-types.toml` (reaction-types "Starter reaction types"), which `init` copies.
