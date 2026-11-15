## MODIFIED Requirements

### Requirement: Content does not need JavaScript
Every procedure, catalogue, taxonomy, term, compound, sequence, help and home page SHALL show all of its content without running JavaScript. Among what scripts add:
- `site/assets/js/site.js` reveals and wires the print button (`window.print()`) and the SMILES copy button.
- `site.js` replaces the print-facts URL with `location.href` when the protocol is `http:` or `https:`.
- The copy button writes the SMILES string with the Clipboard API. When that fails or is unavailable, it selects the SMILES text instead.
- The catalogue script, on the catalogue and term pages, reveals the catalogue's controls and runs its search, filters, sorting and views (site-catalogue).

In the published HTML, the print button (`data-print`) and the SMILES copy button (`data-copy-smiles`) carry `hidden`, and only `site.js` reveals them. No other button carries `hidden`. Every button of a catalogue lies inside an element that carries `data-catalogue-controls` and `hidden`, which only the catalogue script reveals. The header search's submit button is visible and works without JavaScript.

#### Scenario: Static HTML holds the content
- **WHEN** a test scans every procedure page after a theme build, without running scripts
- **THEN** the metadata values, the rendered body sections and the links are present in the HTML, every `button` with `data-print` or `data-copy-smiles` has the `hidden` attribute, and no other `button` on any page under `public/` has it
- **AND** every `button` of a page's `div.catalogue` lies inside an element with `data-catalogue-controls` and `hidden`

#### Scenario: Buttons work in a browser
- **WHEN** the orchestrator opens a procedure page in a browser with JavaScript (manual verification, tasks.md section 6)
- **THEN** the print button is visible and opens the print dialog, the Copy button copies or selects the SMILES string, and with JavaScript disabled neither button is shown and the page is otherwise unchanged
- **AND** with JavaScript disabled, submitting the header search of a procedure page loads `/procedures/?q=<term>`, which shows the `noscript` note and every procedure by ID, and no catalogue control
