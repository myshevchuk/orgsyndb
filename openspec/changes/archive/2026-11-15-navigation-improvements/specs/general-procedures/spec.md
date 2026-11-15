## MODIFIED Requirements

### Requirement: General procedures view
The site SHALL publish `/general-procedures/`, a catalogue page whose rows are the published general procedures, by ID, with the `kind` facet fixed to `general` as a term page fixes its term (site-catalogue "Catalogue pages" and "Fixed scope on term pages"). It opens with the section tabs (site-theme "Procedure section tabs"). Its `h1` and display title are `General procedures`; its scope line reads `Only general procedures`, then ` · ` and the `Browse all procedures` link; its header search is labelled `Search general procedures` with the placeholder `Search these procedures`.

#### Scenario: The view lists the general procedures
- **WHEN** a test scans `public/general-procedures/index.html` after a theme build in locale `en`
- **THEN** its rows are exactly the published general procedures, by ID, its fixed facet is `kind` with the one checked, disabled value `general`, and its scope line and header search carry the stated texts

