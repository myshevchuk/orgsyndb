## MODIFIED Requirements

### Requirement: Navigation and controls are not printed
The print stylesheet SHALL hide the following:
- the site header and navigation;
- the footer;
- the skip link;
- `p.actions` and every `button`;
- any search form;
- the structure placeholder.

It keeps the sample banner, the procedure header, the print facts and the indexed body.

#### Scenario: No chrome in the PDFs
- **WHEN** a test reads all page texts of every PDF after a PDF build
- **THEN** none contains `Skip to content`, `Print / Save as PDF`, `No structure image`, `Search procedures` or `OrgSynDB · internal procedures`, and no line contains both `Procedures` and `Help`
- **AND** the first page of every sample's PDF contains `Sample data — quantities not experimentally verified.`
