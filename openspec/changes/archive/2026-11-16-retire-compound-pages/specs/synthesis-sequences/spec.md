## MODIFIED Requirements

### Requirement: Sequences beside procedures and compounds
A procedure's metadata panel SHALL hold, after `Used in`, the pair `Sequences`, with one `a.sequence` per sequence that has the procedure as a step, linking its page with its title, by ID, and only when there is one. The lab's substance page lists the sequences whose target is the substance (lab-registry "Registry pages").

#### Scenario: Links to the demo sequence
- **WHEN** a test reads the pages of OSDB-0001 and OSDB-0002 after a theme build
- **THEN** both procedure panels have a `Sequences` pair linking `SEQ-0001`
