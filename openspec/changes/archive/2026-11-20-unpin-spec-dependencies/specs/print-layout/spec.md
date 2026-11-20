## MODIFIED Requirements

### Requirement: Warning-free rendering
WeasyPrint SHALL render every procedure page without a warning. No stylesheet a procedure page loads in print media uses a property, value or media query that WeasyPrint does not support.

#### Scenario: Clean pdf run
- **WHEN** a PDF build completes
- **THEN** it exits 0, and no line of its stdout or stderr begins with `WARNING:`
