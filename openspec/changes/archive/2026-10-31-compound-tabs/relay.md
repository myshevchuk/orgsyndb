# Relay record: compound-tabs

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 8026851 | 67674 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 5176444 | 26353 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready | 2 | 2 | 3 | 1 | 4 | 0 |
| Reviewer | no actionable defects; every scenario covered | 0 | 0 | 0 | — | 0 | 0 |

## Hand-backs

- Critic: the living "Procedure section tabs" requirement forbade `nav.section-tabs` on every other page — its delta now allows the compound tabs on the compound catalogue's pages.
- Critic: a tab's rows were defined through the facet attribute, which a tabs field that is no facet lacks — rows now come from the compounds' values; scenario "A tabs field that is not a facet" added.
- Critic: only the single-valued `group` field was exercised — scenario "Tabs by a multiple-valued field" added, with an unused top-level value.
- Critic: the inherited noscript note said the page lists every compound — tab pages have their own.
- Test writer: under a multiple-valued tabs field a tab's own facet can have nothing to list, which the contract left open — decided: such a facet is left out; the spec amended and a test added by the orchestrator before the baseline commit.
- Implementer: `test_field_data_is_staged`, older than the change, still expected five fields — the test contradicted the new fixture; corrected by the orchestrator in its own commit.
- Implementer: settled the shared catalogue partials, the cached row records, the tab pages' `layout = "tab"` and `tab` parameter, the i18n key names, and empty facets dropped on tab pages only — accepted.

## Test boundary

held by the implementer; one stale test corrected by the orchestrator (see hand-backs)
