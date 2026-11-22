## MODIFIED Requirements

### Requirement: Diagram command
`manage.py schema_diagram` SHALL write the table diagram to `webapp/docs/database-schema.html`, creating `webapp/docs/` when it does not exist, and print the path it wrote; `--output <path>` names another file in its place. With `--check` it writes nothing: it exits 0 when the file holds exactly the text the command would write, and otherwise exits 1 with a message naming the file and the command that regenerates it. The text depends only on the models and the generator: it carries no date, commit or path of the machine. The suite runs the check against the committed file, so a change of the models that leaves the diagram stale fails the suite.

#### Scenario: Writing and checking
- **WHEN** a test runs `schema_diagram` with the output path pointed into an empty temporary directory, then `schema_diagram --check` on that path, then changes one byte of the file and checks again, then removes it and checks again
- **THEN** the first run creates the file and prints its path, the first check exits 0, and the second and third exit 1 naming the file and `schema_diagram`

#### Scenario: The committed diagram is current
- **WHEN** the suite runs `schema_diagram --check` against `webapp/docs/database-schema.html`
- **THEN** it exits 0
