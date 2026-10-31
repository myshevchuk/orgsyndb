# Relay record: compound-facets

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 9239291 | 76939 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 6766234 | 35771 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready | 2 | 4 | 5 | 0 | 6 | 0 |
| Reviewer | one P2: results of a facetless catalogue fall into the facet column | 0 | 1 | 0 | — | 1 | 0 |

## Hand-backs

- Critic: a scenario's count ignored the other facet's selection — corrected to 1.
- Critic: the address round trip needed the facets in `known` order — stated.
- Critic: page facets were never taken through `withQuery` and `clear` — scenario added, a state without facets included.
- Critic: "a facet with a selection is open" would reopen a collapsed Status — only facets the page leaves closed open.
- Critic: a value beside its ancestor was not exercised — scenarios added for the rows and the core.
- Critic: inherited scenarios named a task section that does not exist, and the compound walk left the chip unnamed — references corrected, the chip and addresses named, the procedure checks listed in task 3.2.
- Implementer: `test_labels_fall_back_to_the_english_one`, older than the change, still expected values without `ancestors` — the test contradicted the contract; corrected by the orchestrator in its own commit.
- Implementer: settled the i18n key names, the row attributes' construction, the boolean facet values, the record of facets rendered open, and `match` skipping a repeated ID — accepted.
- Browser check (orchestrator, inline): beside the facets the compound table overflowed and broke names mid-word — long words hyphenate (`hyphenate-limit-chars: 12 5 5`) and header cells wrap.
- Reviewer: without facet fields the results fell into the 15rem facet track — reproduced on a facetless demo copy, a failing style test added, the results span the grid when they are the layout's first child.

## Test boundary

held by the implementer; one stale test corrected by the orchestrator (see hand-backs)
